#include "../FollowCamera.hh"
#include <cstdlib>
#include <iostream>

int main(){
  using namespace uav_course;int checks=0;
  const auto require=[&](bool pass,const char *name){checks++;if(!pass){std::cerr<<"FAIL "<<name<<'\n';std::exit(1);}};
  const gz::math::Pose3d body(12,-4,9,0,0,0);
  for(const std::string mode:{"chase","side","top","orbit"}){
    FollowView view;require(view.SetMode(mode,0),"valid mode accepted");
    const auto pose=view.Step(body,0.);
    const auto ray=(view.target-pose.Pos()).Normalized();
    const auto optical=pose.Rot().RotateVector(gz::math::Vector3d::UnitX);
    require(optical.Distance(ray)<1e-9,"optical +X looks at actual target");
    require(pose.Pos().Z()>body.Pos().Z(),"spectator above aircraft");
    require(pose.Pos().Distance(body.Pos())>2.,"spectator clear of propellers");
  }
  FollowView view;view.Step(body,.03);const auto before=view.mode;
  require(!view.SetMode("/uav/servo/9",0)&&view.mode==before,"unknown command cannot become mode");
  auto turned=body;turned.Rot()=gz::math::Quaterniond(0,0,Pi);
  const auto oldEye=view.eye;const auto pose=view.Step(turned,.03);
  require(pose.Pos().Distance(oldEye)<1.,"view switch uses bounded smoothing");
  require(std::abs(Wrap((-Pi+.01)-(Pi-.01))-.02)<1e-12,"yaw wraps shortest way across pi");
  FollowView orbit;orbit.SetMode("orbit",0);const auto start=orbit.Step(body,0.).Pos();
  for(int i=0;i<100;i++)orbit.Step(body,.03);
  require(orbit.eye.Distance(start)>.8,"orbit advances in simulation time");
  const auto frozen=orbit.eye;orbit.Step(body,0.);require(orbit.eye.Distance(frozen)<1e-12,"paused simulation does not advance camera");
  FollowView floor;const auto floorPose=floor.Step(gz::math::Pose3d(0,0,-4,0,0,0),.03);
  require(floorPose.Pos().Z()>=1.3,"camera ground clearance");
  std::cout<<"PASS "<<checks<<" follow geometry/mode checks\n";return 0;
}
