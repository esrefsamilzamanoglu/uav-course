// Ideal camera mount and moving scenery. This system never sets the UAV pose,
// velocity or flight setpoints: its vehicle reference is read-only.
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/World.hh>
#include <gz/sim/Util.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/Utility.hh>
#include <gz/msgs/double.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/plugin/Register.hh>
#include <atomic>
#include <cmath>
#include <memory>
#include <string>

class CourseScene : public gz::sim::System,
                    public gz::sim::ISystemConfigure,
                    public gz::sim::ISystemPreUpdate {
  gz::sim::Entity world{gz::sim::kNullEntity};
  std::string vehicleName{"iris_with_ardupilot"};
  bool rural{false};
  double cameraYawOffset{0.0};
  gz::transport::Node node;
  gz::transport::Node::Publisher posePub;
  std::atomic<double> roll{0.0}, pitch{1.5707963267948966}, yaw{0.0}, pump{0.0};
  double lastPub{-1};
 public:
  void Configure(const gz::sim::Entity &_entity,
                 const std::shared_ptr<const sdf::Element> &_sdf,
                 gz::sim::EntityComponentManager &,
                 gz::sim::EventManager &) override {
    world = _entity;
    if (_sdf->HasElement("vehicle")) vehicleName = _sdf->Get<std::string>("vehicle");
    if (_sdf->HasElement("rural")) rural = _sdf->Get<bool>("rural");
    if (_sdf->HasElement("camera_yaw_offset")) cameraYawOffset = _sdf->Get<double>("camera_yaw_offset");
    node.Subscribe("/course/gimbal/roll", &CourseScene::Roll, this);
    node.Subscribe("/course/gimbal/pitch", &CourseScene::Pitch, this);
    node.Subscribe("/course/gimbal/yaw", &CourseScene::Yaw, this);
    node.Subscribe("/course/pump", &CourseScene::Pump, this);
    posePub = node.Advertise<gz::msgs::Pose>("/course/camera/pose");
  }
  void Roll(const gz::msgs::Double &m) { roll=m.data(); }
  void Pitch(const gz::msgs::Double &m) { pitch=m.data(); }
  void Yaw(const gz::msgs::Double &m) { yaw=m.data(); }
  void Pump(const gz::msgs::Double &m) { pump=m.data(); }
  void PreUpdate(const gz::sim::UpdateInfo &_info,
                 gz::sim::EntityComponentManager &_ecm) override {
    if (_info.paused) return;
    const double t=std::chrono::duration<double>(_info.simTime).count();
    gz::sim::World w(world);
    const auto v=w.ModelByName(_ecm,vehicleName);
    const auto c=w.ModelByName(_ecm,"course_camera");
    if (v!=gz::sim::kNullEntity && c!=gz::sim::kNullEntity) {
      const auto body=gz::sim::worldPose(v,_ecm);
      gz::math::Pose3d camera;
      camera.Pos()=body.Pos()+body.Rot().RotateVector(gz::math::Vector3d(0,0,-0.10));
      camera.Rot()=body.Rot()*gz::math::Quaterniond(0,0,cameraYawOffset)*gz::math::Quaterniond(roll.load(),pitch.load(),yaw.load());
      gz::sim::Model(c).SetWorldPoseCmd(_ecm,camera);
      if (t-lastPub>=0.01) {
        gz::msgs::Pose msg;
        gz::msgs::Set(&msg,camera);
        msg.set_name("course_camera");
        auto stamp=msg.mutable_header()->mutable_stamp();
        stamp->set_sec(static_cast<int64_t>(t));
        stamp->set_nsec(static_cast<int32_t>((t-std::floor(t))*1e9));
        posePub.Publish(msg); lastPub=t;
      }
      const auto spray=w.ModelByName(_ecm,"spray_cloud");
      if (spray!=gz::sim::kNullEntity) {
        auto p=body.Pos();
        p.Z()=pump.load()>0.02 && p.Z()>1.0 ? p.Z()-1.1-std::fmod(t*1.8,0.8) : -12.0;
        gz::sim::Model(spray).SetWorldPoseCmd(_ecm,gz::math::Pose3d(p,gz::math::Quaterniond::Identity));
      }
    }
    if (rural) {
      for (int i=0;i<3;i++) {
        const auto person=w.ModelByName(_ecm,"walker_"+std::to_string(i+1));
        if (person==gz::sim::kNullEntity) continue;
        const double phase=t*(0.8+0.1*i)+8*i;
        const double x=(-30+35*i)+16*std::sin(phase/16);
        const double y=150+70*i+3*std::sin(phase/7);
        const double heading=std::atan2((3.0/7)*std::cos(phase/7),std::cos(phase/16));
        gz::sim::Model(person).SetWorldPoseCmd(_ecm,gz::math::Pose3d(x,y,0,0,0,heading));
      }
    }
  }
};
GZ_ADD_PLUGIN(CourseScene,gz::sim::System,CourseScene::ISystemConfigure,CourseScene::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(CourseScene,"uav_course::CourseScene")
