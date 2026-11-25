// Native Gazebo transport bridge: actual sensor pixels and mechanical telemetry.
// The UDP input is for isolated tests; normal runs use ArduPilot COMMAND topics.
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#endif
#include <gz/transport/Node.hh>
#include <gz/msgs/image.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/msgs/double.pb.h>
#include <gz/msgs/stringmsg.pb.h>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cmath>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <regex>
#include <sstream>
#include <thread>

namespace fs=std::filesystem;
std::atomic<bool> running{true};
double wallTime(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
bool Atomic(const fs::path &path,const std::string &data) {
  const fs::path temp=path.string()+".next";
  {std::ofstream f(temp,std::ios::binary|std::ios::trunc);f.write(data.data(),data.size());if(!f)return false;}
#ifdef _WIN32
  return MoveFileExW(temp.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
#else
  std::error_code ec;fs::rename(temp,path,ec);return !ec;
#endif
}
struct CameraPose{double t,x,y,z,qx,qy,qz,qw;};
struct FollowState{double t;std::string mode,json;};
class Bridge {
  gz::transport::Node node;
  gz::transport::Node::Publisher redPub,bluePub,followModePub;
  fs::path out;
  std::mutex cameraMutex,stateMutex,poseMutex,followMutex;
  std::deque<CameraPose> poses;
  std::deque<FollowState> followStates;
  uint64_t cameraFrames{0},overviewFrames{0},followFrames{0};
  double lastCamera{-1},lastOverview{-1},lastFollow{-1},lastFollowCommand{-1};
  std::string followRequest,followRequestedMode;
 public:
  explicit Bridge(fs::path p):out(std::move(p)) {
    fs::create_directories(out);
    redPub=node.Advertise<gz::msgs::Double>("/uav/servo/9");
    bluePub=node.Advertise<gz::msgs::Double>("/uav/servo/10");
    followModePub=node.Advertise<gz::msgs::StringMsg>("/uav/follow/mode");
    node.Subscribe("/uav/gripper/state",&Bridge::State,this);
    node.Subscribe("/uav/camera/pose",&Bridge::Pose,this);
    node.Subscribe("/course/realistic/camera/image",&Bridge::Camera,this);
    node.Subscribe("/course/realistic/overview/image",&Bridge::Overview,this);
    node.Subscribe("/course/realistic/follow/image",&Bridge::Follow,this);
    node.Subscribe("/uav/follow/state",&Bridge::FollowTelemetry,this);
  }
  void State(const gz::msgs::StringMsg &m) {
    std::lock_guard<std::mutex> lock(stateMutex);
    Atomic(out/"state.json",m.data());
    // Appended evidence is bounded by the runtime session lifetime.
    std::ofstream f(out/"mechanics.jsonl",std::ios::app);f<<m.data()<<'\n';
  }
  void Pose(const gz::msgs::Pose &m) {
    const auto &p=m.position();const auto &q=m.orientation();
    const auto &stamp=m.header().stamp();
    std::lock_guard<std::mutex> lock(poseMutex);
    poses.push_back({stamp.sec()+stamp.nsec()*1e-9,p.x(),p.y(),p.z(),q.x(),q.y(),q.z(),q.w()});
    while(poses.size()>1000)poses.pop_front();
  }
  void FollowTelemetry(const gz::msgs::StringMsg &m) {
    static const std::regex mode("\\\"mode\\\"\\s*:\\s*\\\"(chase|orbit|side|top)\\\"");
    static const std::regex stamp("\\\"sim_time\\\"\\s*:\\s*([0-9.eE+-]+)");
    std::smatch a,b;const auto &json=m.data();
    if(!std::regex_search(json,a,mode)||!std::regex_search(json,b,stamp))return;
    try {
      std::lock_guard<std::mutex> lock(followMutex);
      followStates.push_back({std::stod(b[1]),a[1],json});
      while(followStates.size()>300)followStates.pop_front();
      Atomic(out/"follow-state.json",json);
    }catch(const std::exception &){}
  }
  // kind: 0 onboard, 1 fixed overview, 2 external spectator.
  void Save(const gz::msgs::Image &m,int kind) {
    std::lock_guard<std::mutex> lock(cameraMutex);
    const auto &stamp=m.header().stamp();const double t=stamp.sec()+stamp.nsec()*1e-9;
    const bool overview=kind==1,follow=kind==2;
    auto &last=overview?lastOverview:(follow?lastFollow:lastCamera);
    if(t-last<(overview?.8:(follow?.10:.09)))return;
    const size_t size=static_cast<size_t>(m.width())*m.height()*3;
    if(m.data().size()!=size)return;
    last=t;
    auto &count=overview?overviewFrames:(follow?followFrames:cameraFrames);
    std::ostringstream header;header<<"P6\n"<<m.width()<<' '<<m.height()<<"\n255\n";
    std::string pixels=header.str();pixels+=m.data();
    const std::string prefix=overview?"overview":(follow?"follow":"latest");
    if(!Atomic(out/(prefix+".ppm"),pixels))return;
    CameraPose nearest{};double delta=1e9;
    if(kind==0){std::lock_guard<std::mutex> poseLock(poseMutex);for(const auto &p:poses)if(std::abs(p.t-t)<delta){nearest=p;delta=std::abs(p.t-t);}}
    std::ostringstream meta;meta<<std::setprecision(14)<<"{\"frame\":"<<++count
      <<",\"sim_time\":"<<t<<",\"wall_time\":"<<wallTime()<<",\"width\":"<<m.width()<<",\"height\":"<<m.height()
      <<",\"format\":\"RGB8_PPM\",\"source\":\""<<(follow?"Gazebo external follow camera":"Gazebo camera sensor")<<"\"";
    if(kind==0&&delta<1e8)meta<<",\"pose_delta_s\":"<<delta
      <<",\"position_xyz\":["<<nearest.x<<','<<nearest.y<<','<<nearest.z<<']'
      <<",\"quaternion_xyzw\":["<<nearest.qx<<','<<nearest.qy<<','<<nearest.qz<<','<<nearest.qw<<']';
    if(overview)meta<<",\"purpose\":\"fixed observer map background, not onboard perception\"";
    if(follow) {
      FollowState state{};double age=1e9;
      {std::lock_guard<std::mutex> stateLock(followMutex);for(const auto &p:followStates)if(std::abs(p.t-t)<age){state=p;age=std::abs(p.t-t);}}
      if(age<.10)meta<<",\"mode\":\""<<state.mode<<"\",\"pose_delta_s\":"<<age<<",\"native_state\":"<<state.json;
      meta<<",\"purpose\":\"external spectator only, not onboard perception\"";
    }
    meta<<'}';Atomic(out/(overview?"overview.json":(follow?"follow.json":"camera.json")),meta.str());
  }
  void Camera(const gz::msgs::Image &m){Save(m,0);}
  void Overview(const gz::msgs::Image &m){Save(m,1);}
  void Follow(const gz::msgs::Image &m){Save(m,2);}
  void PollFollow() {
    // File input can only select a spectator mode, never servo / vehicle data.
    std::ifstream f(out/"follow-control.json",std::ios::binary);if(!f)return;
    std::ostringstream data;data<<f.rdbuf();const auto json=data.str();
    static const std::regex mode("\\\"mode\\\"\\s*:\\s*\\\"(chase|orbit|side|top)\\\"");
    std::smatch match;if(!std::regex_search(json,match,mode))return;
    const auto now=wallTime();bool acknowledged=false;
    {std::lock_guard<std::mutex> lock(followMutex);acknowledged=!followStates.empty()&&followStates.back().mode==match[1];}
    if(json==followRequest&&(acknowledged||now-lastFollowCommand<.5))return;
    followRequest=json;followRequestedMode=match[1];lastFollowCommand=now;
    gz::msgs::StringMsg message;message.set_data(followRequestedMode);followModePub.Publish(message);
  }
  void Command(const std::string &json) {
    static const std::regex servo("\\\"servo\\\"\\s*:\\s*(9|10)");
    static const std::regex pwm("\\\"pwm\\\"\\s*:\\s*([0-9]+(?:\\.[0-9]+)?)");
    std::smatch a,b;
    if(!std::regex_search(json,a,servo)||!std::regex_search(json,b,pwm))return;
    const int channel=std::stoi(a[1]);const double value=std::stod(b[1]);
    if(value<900||value>2100)return;
    gz::msgs::Double m;m.set_data(value);
    if(channel==9)redPub.Publish(m);else bluePub.Publish(m);
    std::lock_guard<std::mutex> lock(stateMutex);
    std::ofstream f(out/"test-servo-input.jsonl",std::ios::app);
    f<<"{\"wall_time\":"<<std::setprecision(14)<<wallTime()<<",\"servo\":"<<channel<<",\"pwm\":"<<value<<"}\n";
  }
};
int main(int argc,char **argv) {
  fs::path out;int port=9109;
  for(int i=1;i<argc;i++){
    const std::string arg=argv[i];
    if(arg=="--output-dir"&&i+1<argc)out=argv[++i];
    else if(arg=="--udp-port"&&i+1<argc)port=std::stoi(argv[++i]);
    else {std::cerr<<"usage: realistic_bridge --output-dir DIR [--udp-port 9109]\n";return 2;}
  }
  if(out.empty())return 2;
  std::signal(SIGINT,[](int){running=false;});std::signal(SIGTERM,[](int){running=false;});
  Bridge bridge(out);
#ifdef _WIN32
  WSADATA wsa;if(WSAStartup(MAKEWORD(2,2),&wsa)!=0)return 3;
  SOCKET sock=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
  DWORD timeout=100;setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,reinterpret_cast<const char*>(&timeout),sizeof(timeout));
#else
  int sock=socket(AF_INET,SOCK_DGRAM,0);timeval timeout{0,100000};setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
#endif
  sockaddr_in addr{};addr.sin_family=AF_INET;addr.sin_port=htons(static_cast<unsigned short>(port));addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
  if(bind(sock,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))!=0){std::cerr<<"localhost UDP port occupied: "<<port<<'\n';return 4;}
  std::cout<<"Actual Gazebo RGB/physics bridge ready, localhost UDP"<<port<<" (test control only)\n"<<std::flush;
  while(running){char buffer[2048];const int n=recv(sock,buffer,sizeof(buffer),0);if(n>0)bridge.Command(std::string(buffer,n));bridge.PollFollow();}
#ifdef _WIN32
  closesocket(sock);WSACleanup();
#else
  close(sock);
#endif
  return 0;
}
