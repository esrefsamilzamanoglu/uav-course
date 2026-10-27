// Save actual gz.msgs.Image frames, with timestamped simulator camera poses.
#include <gz/transport/Node.hh>
#include <gz/msgs/image.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/common/Image.hh>
#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <thread>

namespace fs=std::filesystem;
std::atomic<bool> running{true};
struct State { double t,x,y,z,qx,qy,qz,qw; };
class Bridge {
  gz::transport::Node node;
  fs::path out;
  std::mutex mutex,saveMutex;
  std::deque<State> poses;
  uint64_t frames=0,overviews=0;
  double lastCamera=-10,lastOverview=-10;
 public:
  explicit Bridge(fs::path p):out(std::move(p)) {
    fs::create_directories(out/"camera");fs::create_directories(out/"overview");
    node.Subscribe("/course/camera/pose",&Bridge::Pose,this);
    node.Subscribe("/course/camera/image",&Bridge::Image,this);
    node.Subscribe("/course/overview/image",&Bridge::Overview,this);
  }
  void Pose(const gz::msgs::Pose &m) {
    const auto &s=m.header().stamp(); const auto &p=m.position();const auto &q=m.orientation();
    std::lock_guard<std::mutex> lock(mutex);
    poses.push_back({s.sec()+s.nsec()*1e-9,p.x(),p.y(),p.z(),q.x(),q.y(),q.z(),q.w()});
    while(poses.size()>4000)poses.pop_front();
  }
  void Save(const gz::msgs::Image &m,const std::string &kind,uint64_t &counter,double &last,double interval) {
    std::lock_guard<std::mutex> saveLock(saveMutex);
    double t=m.header().stamp().sec()+m.header().stamp().nsec()*1e-9;
    if(t-last<interval)return;last=t;
    if(m.data().size()!=static_cast<size_t>(m.width())*m.height()*3)return;
    std::ostringstream name;name<<std::setfill('0')<<std::setw(6)<<counter++;
    auto path=out/kind/(name.str()+".png");
    gz::common::Image img;
    img.SetFromData(reinterpret_cast<const unsigned char*>(m.data().data()),m.width(),m.height(),gz::common::Image::RGB_INT8);
    img.SavePNG(path.string());
    State nearest{};double delta=1e9;
    {
      std::lock_guard<std::mutex> lock(mutex);
      for(const auto &p:poses)if(std::abs(p.t-t)<delta){nearest=p;delta=std::abs(p.t-t);}
    }
    std::ofstream f(out/(kind+".jsonl"),std::ios::app);
    const double wall=std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
    f<<std::setprecision(15)<<"{\"frame\":\""<<kind<<"/"<<name.str()<<".png\",\"sim_time\":"<<t<<",\"wall_time\":"<<wall
     <<",\"width\":"<<m.width()<<",\"height\":"<<m.height();
    if(kind=="camera")f<<",\"pose_delta_s\":"<<delta
     <<",\"position\":["<<nearest.x<<","<<nearest.y<<","<<nearest.z<<"],\"quaternion_xyzw\":["
     <<nearest.qx<<","<<nearest.qy<<","<<nearest.qz<<","<<nearest.qw<<"]";
    f<<"}\n";
    if(counter%20==0)std::cout<<kind<<" frames="<<counter<<std::endl;
  }
  void Image(const gz::msgs::Image &m){Save(m,"camera",frames,lastCamera,0.20);}
  void Overview(const gz::msgs::Image &m){Save(m,"overview",overviews,lastOverview,3.0);}
};
int main(int argc,char**argv){
  if(argc!=2){std::cerr<<"usage: course_camera_bridge OUTPUT_DIRECTORY\n";return 2;}
  std::signal(SIGINT,[](int){running=false;});std::signal(SIGTERM,[](int){running=false;});
  Bridge bridge(argv[1]);
  std::cout<<"Gazebo Image bridge ready"<<std::endl;
  while(running)std::this_thread::sleep_for(std::chrono::milliseconds(100));
  return 0;
}
