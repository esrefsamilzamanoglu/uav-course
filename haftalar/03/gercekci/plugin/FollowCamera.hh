// External spectator camera geometry. No vehicle pose or actuator commands.
#pragma once
#include <gz/math/Pose3.hh>
#include <algorithm>
#include <cmath>
#include <string>

namespace uav_course {
inline constexpr double Pi=3.14159265358979323846;
inline double Wrap(double a){return std::atan2(std::sin(a),std::cos(a));}
inline bool FollowMode(const std::string &s){return s=="chase"||s=="orbit"||s=="side"||s=="top";}
struct FollowView {
  std::string mode{"chase"};
  gz::math::Vector3d eye,target;
  double pitch{0},yaw{0},orbitPhase{0};
  bool initialized{false};
  bool SetMode(const std::string &value,double heading) {
    if(!FollowMode(value))return false;
    if(value!=mode&&value=="orbit")orbitPhase=heading+Pi;
    mode=value;return true;
  }
  gz::math::Pose3d Step(const gz::math::Pose3d &body,double dt) {
    dt=std::clamp(dt,0.,.20);
    const auto heading=body.Rot().Yaw();
    const gz::math::Vector3d forward(std::cos(heading),std::sin(heading),0);
    const gz::math::Vector3d left(-std::sin(heading),std::cos(heading),0);
    auto wanted=body.Pos()-forward*3.+gz::math::Vector3d(0,0,1.15);
    if(mode=="side")wanted=body.Pos()+left*3.1+gz::math::Vector3d(0,0,.9);
    if(mode=="top")wanted=body.Pos()-forward*.05+gz::math::Vector3d(0,0,5.8);
    if(mode=="orbit") {
      orbitPhase=Wrap(orbitPhase+dt*.16);
      wanted=body.Pos()+gz::math::Vector3d(3.7*std::cos(orbitPhase),3.7*std::sin(orbitPhase),1.3);
    }
    wanted.Z(std::max(1.3,wanted.Z()));
    const auto wantedTarget=body.Pos()+gz::math::Vector3d(0,0,-.26);
    if(!initialized){eye=wanted;target=wantedTarget;}
    else {
      eye+=(wanted-eye)*(1.-std::exp(-dt/.32));
      target+=(wantedTarget-target)*(1.-std::exp(-dt/.075));
    }
    const auto ray=target-eye;
    const double wantedYaw=std::atan2(ray.Y(),ray.X());
    const double wantedPitch=-std::atan2(ray.Z(),std::hypot(ray.X(),ray.Y()));
    if(!initialized){yaw=wantedYaw;pitch=wantedPitch;initialized=true;}
    else {const auto a=1.-std::exp(-dt/.10);yaw=Wrap(yaw+Wrap(wantedYaw-yaw)*a);pitch+=(wantedPitch-pitch)*a;}
    return gz::math::Pose3d(eye,gz::math::Quaterniond(0,pitch,yaw));
  }
};
}
