// Real physical grasp/release: only creates/removes fixed link constraints.
// Vehicle, tether and payload positions are never overwritten by this system.
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/World.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/DetachableJoint.hh>
#include <gz/sim/components/Inertial.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/double.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/msgs/Utility.hh>
#include <gz/plugin/Register.hh>
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <iomanip>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include "FollowCamera.hh"

namespace {
using namespace gz::sim;
struct Grip {
  std::string name;
  int channel;
  std::atomic<double> pwm{1900};
  std::atomic<bool> received{false};
  Entity end{kNullEntity}, mount{kNullEntity}, jaw{kNullEntity};
  Entity joint{kNullEntity}, payload{kNullEntity};
  Entity lastRemovedJoint{kNullEntity};
  std::string payloadName;
  unsigned attachedCount{0}, releasedCount{0};
  double distance{999}, relativeSpeed{0};
  std::string reason{"not_ready"};
  Grip(std::string n,int ch):name(std::move(n)),channel(ch){}
};
Entity Resolve(const std::string &name,const EntityComponentManager &ecm,Entity relative) {
  const auto found=entitiesFromScopedName(name,ecm,relative);
  return found.empty()?kNullEntity:*found.begin();
}
void Vector(std::ostream &s,const gz::math::Vector3d &p) {s<<'['<<p.X()<<','<<p.Y()<<','<<p.Z()<<']';}
void PoseJson(std::ostream &s,const gz::math::Pose3d &p) {
  s<<"{\"position_xyz\":";Vector(s,p.Pos());const auto q=p.Rot();
  s<<",\"quaternion_xyzw\":["<<q.X()<<','<<q.Y()<<','<<q.Z()<<','<<q.W()<<"]}";
}
}

class PayloadMechanics: public System,public ISystemConfigure,
                        public ISystemPreUpdate,public ISystemPostUpdate {
  Entity world{kNullEntity},vehicle{kNullEntity},body{kNullEntity};
  std::string vehicleName{"competition_quad"},bodyName{"iris_with_standoffs::base_link"};
  std::array<Grip,2> grips{{Grip("red",9),Grip("blue",10)}};
  std::array<Entity,2> payloads{{kNullEntity,kNullEntity}};
  std::array<std::string,2> payloadNames{{"payload_red","payload_blue"}};
  std::string payloadLink{"payload_link"};
  std::string commandSource{"ArduPilot JSON servo output"};
  double captureRadius{.16},captureSpeed{.60},lastPublish{-10},lastCamera{-10};
  bool fixtureExcitation{false};
  gz::math::Pose3d cameraLocal{.17,0,-.055,0,1.5707963267948966,0};
  gz::transport::Node node;
  gz::transport::Node::Publisher statePub,cameraPub;
  Entity follow{kNullEntity};
  std::string followModel{"follow_observer"},requestedFollowMode{"chase"};
  std::mutex followMutex;
  uav_course::FollowView followView;
  double lastFollow{-10},lastFollowPublish{-10};
  gz::transport::Node::Publisher followPub;
 public:
  void Configure(const Entity &_entity,const std::shared_ptr<const sdf::Element> &_sdf,
                 EntityComponentManager &,EventManager &) override {
    world=_entity;
    if(_sdf->HasElement("vehicle"))vehicleName=_sdf->Get<std::string>("vehicle");
    if(_sdf->HasElement("body_link"))bodyName=_sdf->Get<std::string>("body_link");
    if(_sdf->HasElement("payload_link"))payloadLink=_sdf->Get<std::string>("payload_link");
    if(_sdf->HasElement("command_source"))commandSource=_sdf->Get<std::string>("command_source");
    if(_sdf->HasElement("capture_radius"))captureRadius=_sdf->Get<double>("capture_radius");
    if(_sdf->HasElement("capture_speed"))captureSpeed=_sdf->Get<double>("capture_speed");
    if(_sdf->HasElement("camera_pose"))cameraLocal=_sdf->Get<gz::math::Pose3d>("camera_pose");
    if(_sdf->HasElement("follow_model"))followModel=_sdf->Get<std::string>("follow_model");
    if(_sdf->HasElement("initial_closed")&&!_sdf->Get<bool>("initial_closed"))for(auto &g:grips)g.pwm=1100;
    if(_sdf->HasElement("fixture_excitation"))fixtureExcitation=_sdf->Get<bool>("fixture_excitation");
    node.Subscribe("/uav/servo/9",&PayloadMechanics::Servo9,this);
    node.Subscribe("/uav/servo/10",&PayloadMechanics::Servo10,this);
    statePub=node.Advertise<gz::msgs::StringMsg>("/uav/gripper/state");
    cameraPub=node.Advertise<gz::msgs::Pose>("/uav/camera/pose");
    followPub=node.Advertise<gz::msgs::StringMsg>("/uav/follow/state");
    node.Subscribe("/uav/follow/mode",&PayloadMechanics::FollowMode,this);
  }
  void FollowMode(const gz::msgs::StringMsg &m) {
    if(!uav_course::FollowMode(m.data()))return;
    std::lock_guard<std::mutex> lock(followMutex);requestedFollowMode=m.data();
  }
  void Servo9(const gz::msgs::Double &m){grips[0].pwm=m.data();grips[0].received=true;}
  void Servo10(const gz::msgs::Double &m){grips[1].pwm=m.data();grips[1].received=true;}
  void PreUpdate(const UpdateInfo &info,EntityComponentManager &ecm) override {
    if(info.paused)return;
    const auto t=std::chrono::duration<double>(info.simTime).count();
    if(vehicle==kNullEntity)vehicle=World(world).ModelByName(ecm,vehicleName);
    if(vehicle==kNullEntity)return;
    if(body==kNullEntity)body=Resolve(bodyName,ecm,vehicle);
    // Only the dedicated, massless external observer receives pose commands.
    // map_observer and every aircraft / cargo entity remain untouched.
    if(follow==kNullEntity)follow=World(world).ModelByName(ecm,followModel);
    if(follow!=kNullEntity&&body!=kNullEntity&&(t-lastFollow>=.03||t<lastFollow)) {
      const auto current=worldPose(body,ecm);
      {std::lock_guard<std::mutex> lock(followMutex);followView.SetMode(requestedFollowMode,current.Rot().Yaw());}
      const auto dt=lastFollow<0?.03:std::max(0.,t-lastFollow);
      Model(follow).SetWorldPoseCmd(ecm,followView.Step(current,dt));lastFollow=t;
    }
    for(size_t i=0;i<payloads.size();i++) {
      if(payloads[i]==kNullEntity) {
        const auto model=World(world).ModelByName(ecm,payloadNames[i]);
        if(model!=kNullEntity)payloads[i]=Model(model).LinkByName(ecm,payloadLink);
      }
      if(payloads[i]!=kNullEntity)Link(payloads[i]).EnableVelocityChecks(ecm);
    }
    for(auto &g:grips) {
      if(g.end==kNullEntity)g.end=Resolve(g.name+"_gripper",ecm,vehicle);
      if(g.mount==kNullEntity)g.mount=Resolve(g.name+"_mount",ecm,vehicle);
      if(g.jaw==kNullEntity)g.jaw=Resolve(g.name+"_jaw_joint",ecm,vehicle);
      if(g.end==kNullEntity){g.reason="gripper_link_missing";continue;}
      Link(g.end).EnableVelocityChecks(ecm);
      const auto pwm=g.pwm.load();
      bool jawClosed=true;
      if(g.jaw!=kNullEntity) {
        const auto pos=ecm.Component<components::JointPosition>(g.jaw);
        if(!pos)ecm.CreateComponent(g.jaw,components::JointPosition());
        const auto angle=pos&&!pos->Data().empty()?pos->Data()[0]:0.;
        jawClosed=angle<.12;
        const auto target=pwm>=1700?0.:(pwm<=1300?.6:angle);
        auto cmd=ecm.Component<components::JointVelocityCmd>(g.jaw);
        const std::vector<double> speed{std::clamp((target-angle)*8.,-2.,2.)};
        if(cmd)cmd->Data()=speed;else ecm.CreateComponent(g.jaw,components::JointVelocityCmd(speed));
      }
      if(pwm<=1300) {
        if(g.joint!=kNullEntity) {
          g.lastRemovedJoint=g.joint;ecm.RequestRemoveEntity(g.joint);g.joint=kNullEntity;g.payload=kNullEntity;
          g.payloadName.clear();g.releasedCount++;
        }
        g.reason="open";continue;
      }
      if(pwm<1700){g.reason=g.joint!=kNullEntity?"holding":"neutral";continue;}
      if(g.joint!=kNullEntity){g.reason="holding";continue;}
      if(!jawClosed){g.reason="jaw_closing";continue;}
      // Candidate search is geometric, never the camera or mission's target truth.
      const auto endPose=worldPose(g.end,ecm);
      double nearest=1e10;Entity candidate=kNullEntity;size_t index=0;
      for(size_t i=0;i<payloads.size();i++) {
        const auto e=payloads[i];if(e==kNullEntity)continue;
        bool claimed=false;for(const auto &other:grips)if(other.payload==e)claimed=true;
        if(claimed)continue;
        const auto p=worldPose(e,ecm);
        const auto point=p.Pos()+p.Rot().RotateVector(gz::math::Vector3d(0,0,.08));
        const auto dist=point.Distance(endPose.Pos());
        if(dist<nearest){nearest=dist;candidate=e;index=i;}
      }
      g.distance=nearest<1e9?nearest:999.;
      if(candidate==kNullEntity){g.reason="no_available_payload";continue;}
      const auto velocity=Link(g.end).WorldLinearVelocity(ecm);
      const auto cargoVelocity=Link(candidate).WorldLinearVelocity(ecm);
      if(!velocity||!cargoVelocity){g.reason="velocity_not_ready";continue;}
      g.relativeSpeed=(*velocity-*cargoVelocity).Length();
      if(g.distance>captureRadius){g.reason="outside_capture_radius";continue;}
      if(g.relativeSpeed>captureSpeed){g.reason="relative_speed_high";continue;}
      g.joint=ecm.CreateEntity();
      ecm.CreateComponent(g.joint,components::DetachableJoint({g.end,candidate,"fixed"}));
      // DART supports DetachableJoint itself; do not request the optional
      // SetFixedJointWeldChildToParent feature absent from this native backend.
      g.payload=candidate;g.payloadName=payloadNames[index];g.attachedCount++;g.reason="attached";
    }
    // Test-only calibrated force excites a pendulum; no pose/velocity overwrite.
    if(fixtureExcitation&&t>1.&&t<1.15&&payloads[0]!=kNullEntity)
      Link(payloads[0]).AddWorldForce(ecm,gz::math::Vector3d(1.3,0,0));
  }
  void PostUpdate(const UpdateInfo &info,const EntityComponentManager &ecm) override {
    if(info.paused||vehicle==kNullEntity||body==kNullEntity)return;
    const auto t=std::chrono::duration<double>(info.simTime).count();
    const auto bodyPose=worldPose(body,ecm);
    const auto cameraPose=bodyPose*cameraLocal;
    if(follow!=kNullEntity&&followView.initialized&&t-lastFollowPublish>=.03) {
      const auto actual=worldPose(follow,ecm);
      std::ostringstream f;f<<std::setprecision(14)<<"{\"sim_time\":"<<t<<",\"mode\":\""<<followView.mode
        <<"\",\"source\":\"Gazebo external follow camera\",\"camera_pose\":";
      PoseJson(f,actual);f<<",\"eye_enu\":";Vector(f,actual.Pos());
      f<<",\"target_enu\":";Vector(f,followView.target);f<<'}';
      gz::msgs::StringMsg message;message.set_data(f.str());followPub.Publish(message);lastFollowPublish=t;
    }
    if(t-lastCamera>=.009) {
      gz::msgs::Pose m;gz::msgs::Set(&m,cameraPose);m.set_name("physical_rgb_camera");
      m.mutable_header()->mutable_stamp()->set_sec(static_cast<int64_t>(t));
      m.mutable_header()->mutable_stamp()->set_nsec(static_cast<int32_t>((t-std::floor(t))*1e9));
      cameraPub.Publish(m);lastCamera=t;
    }
    if(t-lastPublish<.05)return;lastPublish=t;
    std::ostringstream s;s<<std::setprecision(12)<<"{\"sim_time\":"<<t<<",\"vehicle_pose\":";
    PoseJson(s,bodyPose);s<<",\"camera_pose\":";PoseJson(s,cameraPose);
    s<<",\"capture_radius_m\":"<<captureRadius<<",\"capture_speed_m_s\":"<<captureSpeed<<",\"grippers\":[";
    for(size_t i=0;i<grips.size();i++) {
      const auto &g=grips[i];if(i)s<<',';
      s<<"{\"id\":\""<<g.name<<"\",\"servo\":"<<g.channel<<",\"pwm\":"<<g.pwm.load()
       <<",\"command_received\":"<<(g.received.load()?"true":"false")
       <<",\"command_source\":\""<<(g.received.load()?commandSource:"mechanical preload default")<<"\""
       <<",\"attached\":"<<(g.joint!=kNullEntity?"true":"false")
       <<",\"joint_entity\":"<<g.joint
       <<",\"joint_entity_alive\":"<<(g.joint!=kNullEntity&&ecm.HasEntity(g.joint)?"true":"false")
       <<",\"last_removed_joint_entity\":"<<g.lastRemovedJoint
       <<",\"last_removed_joint_alive\":"<<(g.lastRemovedJoint!=kNullEntity&&ecm.HasEntity(g.lastRemovedJoint)?"true":"false")
       <<",\"payload\":"<<(g.payloadName.empty()?"null":"\""+g.payloadName+"\"")
       <<",\"distance_m\":"<<g.distance<<",\"relative_speed_m_s\":"<<g.relativeSpeed
       <<",\"attach_count\":"<<g.attachedCount<<",\"release_count\":"<<g.releasedCount
       <<",\"reason\":\""<<g.reason<<"\"";
      if(g.jaw!=kNullEntity) {
        const auto angle=ecm.Component<components::JointPosition>(g.jaw);
        if(angle&&!angle->Data().empty())s<<",\"jaw_angle_rad\":"<<angle->Data()[0];
        const auto velocity=ecm.Component<components::JointVelocityCmd>(g.jaw);
        if(velocity&&!velocity->Data().empty())s<<",\"jaw_velocity_command_rad_s\":"<<velocity->Data()[0];
      }
      if(g.end!=kNullEntity){s<<",\"position_xyz\":";Vector(s,worldPose(g.end,ecm).Pos());}
      if(g.mount!=kNullEntity&&g.end!=kNullEntity) {
        const auto mount=worldPose(g.mount,ecm).Pos();const auto delta=worldPose(g.end,ecm).Pos()-mount;
        const auto swing=delta.Length()>1e-6?std::acos(std::clamp(-delta.Z()/delta.Length(),-1.,1.))*180./3.141592653589793:0.;
        s<<",\"mount_xyz\":";Vector(s,mount);s<<",\"swing_deg\":"<<swing;
      }
      s<<'}';
    }
    s<<"],\"payloads\":[";
    for(size_t i=0;i<payloads.size();i++) {
      if(i)s<<',';s<<"{\"id\":\""<<payloadNames[i]<<"\",\"available\":"<<(payloads[i]!=kNullEntity?"true":"false");
      if(payloads[i]!=kNullEntity) {
        s<<",\"pose\":";PoseJson(s,worldPose(payloads[i],ecm));
        const auto inertial=ecm.Component<components::Inertial>(payloads[i]);
        if(inertial)s<<",\"mass_kg\":"<<inertial->Data().MassMatrix().Mass();
        const auto velocity=Link(payloads[i]).WorldLinearVelocity(ecm).value_or(gz::math::Vector3d::Zero);
        s<<",\"velocity_xyz\":";Vector(s,velocity);
      }s<<'}';
    }
    s<<"]}";gz::msgs::StringMsg m;m.set_data(s.str());statePub.Publish(m);
  }
};
GZ_ADD_PLUGIN(PayloadMechanics,System,PayloadMechanics::ISystemConfigure,
              PayloadMechanics::ISystemPreUpdate,PayloadMechanics::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(PayloadMechanics,"uav_course::PayloadMechanics")
