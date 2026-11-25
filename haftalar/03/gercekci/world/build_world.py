"""Build a populated physical Gazebo competition field and a detailed quadcopter.

The flight controller's native rotor/IMU model is retained. New visuals do not
replace the flight dynamics. Cargo links are genuine dynamic pendulums and all
payloads have mass, inertia, friction and collision geometry.
"""
from __future__ import annotations
import argparse,copy,json,math,random,struct
from pathlib import Path
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
ASSETS=ROOT/'models/competition_assets'
SCENE=ROOT/'world/scene.json'
RNG=random.Random(2026)
PALETTE={'ivory':(.91,.93,.94),'navy':(.055,.075,.10),'metal':(.35,.39,.42),
 'rubber':(.025,.03,.035),'glass':(.12,.24,.30),'orange':(.98,.43,.08),
 'concrete':(.53,.55,.53),'white':(.88,.9,.89),'red':(.68,.045,.07),'blue':(.035,.15,.73),
 'wood':(.30,.18,.075),'leaf':(.19,.30,.085),'leaf_light':(.27,.37,.12)}

def sub(parent,tag,text=None,**attrs):
    el=E.SubElement(parent,tag,attrs)
    if text is not None:el.text=str(text)
    return el
def vec(v):return ' '.join(f'{float(x):.8g}' for x in v)
def pose(parent,xyz=(0,0,0),rpy=(0,0,0)):sub(parent,'pose',vec((*xyz,*rpy)))
def material(vis,color,metal=0,rough=.75,texture=None):
    color=PALETTE.get(color,color)
    mat=sub(vis,'material');rgba=vec((*color[:3],1))
    sub(mat,'ambient',rgba);sub(mat,'diffuse',rgba);sub(mat,'specular','.14 .14 .14 1')
    pbr=sub(sub(mat,'pbr'),'metal');sub(pbr,'metalness',metal);sub(pbr,'roughness',rough)
    if texture:sub(pbr,'albedo_map',texture)
def geometry(parent,shape,size):
    geo=sub(parent,'geometry');g=sub(geo,shape)
    if shape=='box':sub(g,'size',vec(size))
    elif shape=='cylinder':sub(g,'radius',size[0]);sub(g,'length',size[1])
    elif shape=='sphere':sub(g,'radius',size[0])
    elif shape=='plane':sub(g,'normal','0 0 1');sub(g,'size',vec(size))
    elif shape=='mesh':sub(g,'uri',size[0]);sub(g,'scale',vec(size[1] if len(size)>1 else (1,1,1)))
    return g
def visual(link,name,xyz,size,color='white',shape='box',rpy=(0,0,0),metal=0,rough=.75,texture=None):
    v=sub(link,'visual',name=name);pose(v,xyz,rpy);geometry(v,shape,size);material(v,color,metal,rough,texture);return v
def collision(link,name,xyz,size,shape='box',rpy=(0,0,0),mu=.8):
    c=sub(link,'collision',name='collision_'+name);pose(c,xyz,rpy);geometry(c,shape,size)
    surf=sub(c,'surface');fric=sub(sub(surf,'friction'),'ode');sub(fric,'mu',mu);sub(fric,'mu2',mu)
    ode=sub(sub(surf,'contact'),'ode');sub(ode,'max_vel',.3);sub(ode,'min_depth',.001)
    return c
def inertial(link,mass,size=(.1,.1,.1)):
    i=sub(link,'inertial');sub(i,'mass',mass);m=mass;x,y,z=size
    inertia=sub(i,'inertia')
    for key,value in dict(ixx=m*(y*y+z*z)/12,iyy=m*(x*x+z*z)/12,izz=m*(x*x+y*y)/12,ixy=0,ixz=0,iyz=0).items():sub(inertia,key,max(value,1e-7) if key in ('ixx','iyy','izz') else value)
def model(world,name,xyz=(0,0,0),yaw=0,static=True):
    m=sub(world,'model',name=name);sub(m,'static',str(static).lower());pose(m,xyz,(0,0,yaw));return m,sub(m,'link',name='body')
def beam(link,name,a,b,r,color='metal',collision_enabled=False):
    delta=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(x*x for x in delta));mid=[(a[i]+b[i])/2 for i in range(3)]
    yaw=math.atan2(delta[1],delta[0]);pitch=math.acos(max(-1,min(1,delta[2]/length)))
    visual(link,name,mid,(r,length),color,'cylinder',(0,pitch,yaw),metal=.25,rough=.48)
    if collision_enabled:collision(link,name+'_collision',mid,(r,length),'cylinder',(0,pitch,yaw))

class Mesh:
    def __init__(self):self.triangles=[]
    def tri(self,a,b,c):self.triangles.append((a,b,c))
    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('wb') as f:
            f.write(b'UAV course procedural mesh, metre units'.ljust(80,b'\0'));f.write(struct.pack('<I',len(self.triangles)))
            for a,b,c in self.triangles:
                u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
                norm=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.sqrt(sum(n*n for n in norm)) or 1
                f.write(struct.pack('<12fH',*[n/length for n in norm],*a,*b,*c,0))
def meshes():
    d=ASSETS/'meshes';d.mkdir(parents=True,exist_ok=True)
    # Rounded 3D foliage/canopy parts have enough segments for natural shading.
    sphere=Mesh();lat=14;lon=24
    for i in range(lat):
        aa=-math.pi/2+i*math.pi/lat;bb=aa+math.pi/lat
        for j in range(lon):
            u=j*2*math.pi/lon;v=(j+1)*2*math.pi/lon
            def p(a,t):return (math.cos(a)*math.cos(t),math.cos(a)*math.sin(t),math.sin(a))
            sphere.tri(p(aa,u),p(bb,v),p(bb,u));sphere.tri(p(aa,u),p(aa,v),p(bb,v))
    sphere.save(d/'unit_sphere.stl')
    canopy=Mesh();rings=[]
    for x,ry,rz,zc in [(-.19,.025,.025,.025),(-.13,.092,.06,.055),(-.03,.116,.075,.065),(.09,.105,.067,.058),(.18,.05,.035,.04),(.21,.008,.012,.025)]:
        rings.append([(x,ry*math.cos(j*2*math.pi/16),zc+rz*math.sin(j*2*math.pi/16)) for j in range(16)])
    for a,b in zip(rings,rings[1:]):
        for i in range(16):j=(i+1)%16;canopy.tri(a[i],b[j],b[i]);canopy.tri(a[i],a[j],b[j])
    for ring,invert in [(rings[0],True),(rings[-1],False)]:
        center=tuple(sum(v[i] for v in ring)/len(ring) for i in range(3))
        for i in range(16):
            a,b=ring[i],ring[(i+1)%16];canopy.tri(center,b,a) if invert else canopy.tri(center,a,b)
    canopy.save(d/'quad_canopy.stl')
    # Pitched roof solid and four-sided car body both receive dedicated materials.
    roof=Mesh();p=[(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0),(-.5,0,.35),(.5,0,.35)]
    for a,b,c in [(0,1,5),(0,5,4),(4,5,2),(4,2,3),(0,4,3),(1,2,5),(0,3,2),(0,2,1)]:roof.tri(p[a],p[b],p[c])
    roof.save(d/'gable_roof.stl')
    car=Mesh();sections=[(-2.15,.68,.6),(-1.75,.86,.88),(-.85,.85,.96),(-.35,.75,1.48),(.95,.73,1.48),(1.55,.83,.98),(2.12,.73,.85)]
    rr=[]
    for x,y,z in sections:rr.append([(x,-y,.37),(x,y,.37),(x,y,z),(x,-y,z)])
    for a,b in zip(rr,rr[1:]):
        for i in range(4):j=(i+1)%4;car.tri(a[i],b[j],b[i]);car.tri(a[i],a[j],b[j])
    car.tri(rr[0][0],rr[0][2],rr[0][1]);car.tri(rr[0][0],rr[0][3],rr[0][2])
    car.tri(rr[-1][0],rr[-1][1],rr[-1][2]);car.tri(rr[-1][0],rr[-1][2],rr[-1][3])
    car.save(d/'car_body.stl')
    # Ground OBJ supplies physical metre-scale repeated UVs rather than stretching
    # a single tiny grass photograph across the entire competition area.
    (d/'grass_tile.obj').write_text('mtllib grass_tile.mtl\no grass\nv -500 -500 0\nv 500 -500 0\nv 500 500 0\nv -500 500 0\nvt 0 0\nvt 125 0\nvt 125 125\nvt 0 125\nvn 0 0 1\nusemtl Grass\nf 1/1/1 2/2/1 3/3/1\nf 1/1/1 3/3/1 4/4/1\n',encoding='ascii')
    (d/'grass_tile.mtl').write_text('newmtl Grass\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 2\nmap_Kd ../textures/grass_albedo.png\n',encoding='ascii')

def drone(source):
    old=E.parse(REPO/'haftalar/02/simulasyon/worlds/farm.sdf').getroot().find('world/model[@name="iris_with_ardupilot"]')
    quad=copy.deepcopy(old);quad.set('name','competition_quad');quad.find('pose').text='-24 0 .9 0 0 1.57079632679';quad.find('pose').attrib.pop('degrees',None)
    base=quad.find('model/link[@name="base_link"]')
    for v in list(base.findall('visual')):
        if v.get('name')=='base_visual':base.remove(v)
    visual(base,'aero_white_canopy',(0,0,0),('model://competition_assets/meshes/quad_canopy.stl',),'ivory','mesh',metal=.1,rough=.27)
    visual(base,'carbon_belly',(.005,0,-.025),(.29,.205,.055),'navy',metal=.28,rough=.4)
    visual(base,'canopy_dark_centerline',(-.035,0,.137),(.19,.011,.003),'metal',rough=.24)
    for i,(x,y) in enumerate([(.13,-.22),(-.13,.2),(.13,.22),(-.13,-.2)]):
        beam(base,f'carbon_arm_{i}',(x*.25,y*.25,.006),(x,y,.018),.016,'navy')
        visual(base,f'motor_{i}',(x,y,.02),(.027,.05),'navy','cylinder',metal=.65,rough=.24)
        visual(base,f'orange_motor_ring_{i}',(x,y,.043),(.028,.008),'orange','cylinder',metal=.25,rough=.32)
        visual(base,f'arm_fairing_{i}',(x*.50,y*.50,.025),(.073,.027,.03),'ivory',rpy=(0,0,math.atan2(y,x)),metal=.1,rough=.3)
    for i,(x,y) in enumerate([(.123,.22),(.123,-.22),(-.140,.21),(-.140,-.21)]):
        visual(base,f'orange_foot_{i}',(x,y,-.189),(.008,.035),'orange','cylinder',rough=.4)
        # Landing on bare ground must put weight on the airframe, not fold the
        # empty pendulums. Gear is fixed geometry of the existing lumped body:
        # no additional dynamic links, mass or changes to native motor inertia.
        # Splayed rods clear the cargo swing envelope; there are no transverse
        # bars to hook a cargo eye. Wide feet also resist touchdown tipping.
        toe=(math.copysign(.48,x),math.copysign(.48,y),-.831)
        beam(base,f'landing_strut_{i}',(x,y,-.10),toe,.007,'navy',True)
        visual(base,f'landing_foot_{i}',toe,(.014,),'rubber','sphere',rough=.9)
        collision(base,f'landing_foot_{i}',toe,(.014,),'sphere',mu=.7)
    beam(base,'forward_camera_boom',(.15,0,-.04),(.38,0,-.06),.009,'navy',True)
    visual(base,'camera_gimbal_bracket',(.38,0,-.06),(.078,.078,.025),'metal',metal=.55,rough=.3)
    visual(base,'camera_housing',(.38,0,-.079),(.058,.062,.045),'navy',metal=.15,rough=.25)
    collision(base,'camera_housing',(.38,0,-.079),(.058,.062,.045))
    visual(base,'lens_barrel',(.38,0,-.108),(.021,.018),'metal','cylinder',metal=.65,rough=.17)
    visual(base,'lens_glass',(.38,0,-.119),(.017,.003),'glass','cylinder',metal=.7,rough=.05)
    cam=sub(base,'sensor',name='rgb_camera',type='camera');pose(cam,(.38,0,-.13),(0,math.pi/2,0));sub(cam,'always_on','true');sub(cam,'update_rate',8);sub(cam,'topic','/course/realistic/camera/image')
    c=sub(cam,'camera');sub(c,'horizontal_fov',math.pi/2);im=sub(c,'image');sub(im,'width',960);sub(im,'height',720);sub(im,'format','R8G8B8');clip=sub(c,'clip');sub(clip,'near',.04);sub(clip,'far',450)
    # Two gimballed suspension rods: x/y revolute axes make an honest pendulum.
    for color,y in [('red',-.16),('blue',.16)]:
        mount=sub(quad,'link',name=color+'_mount');pose(mount,(0,y,-.05));inertial(mount,.012,(.04,.04,.025));visual(mount,'mount',(0,0,0),(.045,.045,.027),'metal',metal=.6)
        joint=sub(quad,'joint',name=color+'_mount_joint',type='fixed');sub(joint,'parent','iris_with_standoffs::base_link');sub(joint,'child',color+'_mount')
        gimbal=sub(quad,'link',name=color+'_gimbal');pose(gimbal,(0,y,-.05));inertial(gimbal,.004,(.025,.025,.025));visual(gimbal,'pivot',(0,0,0),(.016,),'orange','sphere',metal=.4)
        tether=sub(quad,'link',name=color+'_tether');pose(tether,(0,y,-.325));inertial(tether,.012,(.016,.016,.55));visual(tether,'cable',(0,0,0),(.006,.55),'metal','cylinder',metal=.6,rough=.3);collision(tether,'cable_collision',(0,0,0),(.006,.55),'cylinder',mu=.35)
        for suffix,parent,child,axis in [('swing_x',color+'_mount',color+'_gimbal','1 0 0'),('swing_y',color+'_gimbal',color+'_tether','0 1 0')]:
            j=sub(quad,'joint',name=color+'_'+suffix,type='revolute');sub(j,'parent',parent);sub(j,'child',child)
            # Joint anchor is always at the upper end of the tether.
            p=sub(j,'pose','0 0 '+('.275' if suffix=='swing_y' else '0')+' 0 0 0');p.set('relative_to',child)
            a=sub(j,'axis');sub(a,'xyz',axis);limits=sub(a,'limit');sub(limits,'lower',-1.2);sub(limits,'upper',1.2);sub(limits,'effort',2);sub(limits,'velocity',10);sub(sub(a,'dynamics'),'damping',.025)
        grip=sub(quad,'link',name=color+'_gripper');pose(grip,(0,y,-.60));inertial(grip,.035,(.06,.06,.05));visual(grip,'servo_case',(0,0,0),(.055,.045,.035),'navy',metal=.2,rough=.3)
        # Straight fixed finger + outward-opening jaw allow the lifting eye
        # to fall free. A permanent U-hook would still support its transverse
        # bar even after detaching the physics joint.
        beam(grip,'fixed_finger',(-.028,0,-.01),(-.028,0,-.072),.005,'metal',True)
        joint=sub(quad,'joint',name=color+'_gripper_joint',type='fixed');sub(joint,'parent',color+'_tether');sub(joint,'child',color+'_gripper')
        jaw=sub(quad,'link',name=color+'_jaw');pose(jaw,(.025,y,-.605));inertial(jaw,.005,(.01,.018,.065));beam(jaw,'finger',(0,0,0),(0,0,-.065),.0045,'orange',True)
        j=sub(quad,'joint',name=color+'_jaw_joint',type='revolute');sub(j,'parent',color+'_gripper');sub(j,'child',color+'_jaw');a=sub(j,'axis');sub(a,'xyz','0 -1 0');lim=sub(a,'limit');sub(lim,'lower',0);sub(lim,'upper',.65);sub(lim,'effort',.25);sub(lim,'velocity',3);sub(sub(a,'dynamics'),'damping',.015)
    ap=quad.find('plugin[@name="ArduPilotPlugin"]')
    for ctrl in list(ap.findall('control')):
        if int(ctrl.get('channel','0'))>=8:ap.remove(ctrl)
    for channel,color in [(8,'red'),(9,'blue')]:
        ctrl=sub(ap,'control',channel=str(channel));sub(ctrl,'jointName',color+'_jaw_joint');sub(ctrl,'type','COMMAND');sub(ctrl,'multiplier',1000);sub(ctrl,'offset',1);sub(ctrl,'servo_min',1000);sub(ctrl,'servo_max',2000);sub(ctrl,'cmd_topic','/uav/servo/'+str(channel+1))
    out=ROOT/'models/competition_quad/model.sdf';out.parent.mkdir(parents=True,exist_ok=True);r=E.Element('sdf',version='1.9');r.append(copy.deepcopy(quad));E.indent(r);E.ElementTree(r).write(out,encoding='utf-8',xml_declaration=True)
    (out.parent/'model.config').write_text('<?xml version="1.0"?><model><name>Competition Quad</name><version>1.0</version><sdf version="1.9">model.sdf</sdf><description>White composite quad with real native Iris actuators and double pendulum cargo grippers.</description></model>',encoding='utf-8')
    return quad

def payload(world,color,xyz):
    m=sub(world,'model',name='payload_'+color);sub(m,'static','false');pose(m,xyz);link=sub(m,'link',name='payload_link');inertial(link,.3,(.16,.16,.16));sub(link,'velocity_decay')
    visual(link,'unmarked_'+color,(0,0,0),(.16,.16,.16),color,rough=.86)
    collision(link,'payload_collision',(0,0,0),(.16,.16,.16),mu=.85)
    # Same-colour structural lifting eye, no marker/QR/electronics.
    for i,(a,b) in enumerate([((-.035,0,.08),(-.035,0,.13)),((.035,0,.08),(.035,0,.13)),((-.035,0,.13),(.035,0,.13))]):beam(link,'lift_eye_'+str(i),a,b,.006,color,True)
    return m

def generate(out=None,source=None,plugin_path=None,seed=2026,physics_plugin='PayloadMechanics'):
    global RNG
    RNG=random.Random(seed);source=Path(source or REPO/'windows/.local/ardupilot_gazebo');meshes();scene=json.loads(SCENE.read_text(encoding='utf-8'));scene['objects']=[]
    root=E.Element('sdf',version='1.9');world=sub(root,'world',name=scene['world_name']);physics=sub(world,'physics',name='accurate_1ms',type='ignore');sub(physics,'max_step_size',.001);sub(physics,'real_time_factor',1)
    for filename,name in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('imu','Imu'),('navsat','NavSat')]:sub(world,'plugin',filename='gz-sim-'+filename+'-system',name='gz::sim::systems::'+name)
    sensor=sub(world,'plugin',filename='gz-sim-sensors-system',name='gz::sim::systems::Sensors');sub(sensor,'render_engine','ogre2')
    sc=sub(world,'scene');sub(sc,'ambient','.58 .62 .69 1');sub(sc,'background','.62 .77 .91 1');sub(sc,'shadows','true');sky=sub(sc,'sky');sub(sky,'time',10);sub(sky,'sunrise',6);sub(sky,'sunset',19);sub(sky,'clouds')
    spherical=sub(world,'spherical_coordinates');sub(spherical,'surface_model','EARTH_WGS84');sub(spherical,'latitude_deg',-35.363262);sub(spherical,'longitude_deg',149.165237);sub(spherical,'elevation',584);sub(spherical,'heading_deg',0)
    sun=sub(world,'light',name='clear_autumn_sun',type='directional');pose(sun,(0,0,300));sub(sun,'cast_shadows','true');sub(sun,'diffuse','.96 .92 .83 1');sub(sun,'specular','.3 .29 .27 1');sub(sun,'direction','-.33 .23 -.915')
    def item(kind,name,xyz,size,color,yaw=0,solid=False):
        m,l=model(world,name,xyz,yaw);visual(l,'shape',(0,0,0),size,color)
        if solid:collision(l,'collision',(0,0,0),size)
        cc=PALETTE.get(color,color);scene['objects'].append(dict(type=kind,name=name,position_enu=list(xyz),size=list(size),color=list(cc),yaw=yaw));return m,l
    m,l=model(world,'landscape_ground');visual(l,'textured_grass',(0,0,-.005),('model://competition_assets/meshes/grass_tile.obj',),'white','mesh',texture='model://competition_assets/textures/grass_albedo.png',rough=1);collision(l,'ground',(0,0,-.08),(1400,1400,.16),mu=.9)
    # Mown field boundary, home pad and disjoint search area are physical surfaces.
    for y in [-150,150]:item('boundary','boundary_n_'+str(y),(0,y,.012),(200,.12,.015),'white')
    for x in [-100,100]:item('boundary','boundary_e_'+str(x),(x,0,.012),(.12,300,.015),'white')
    item('home','home_pad',(-24,0,.015),(3.4,3.4,.025),'concrete',solid=True)
    # Flat HOME pad only. The quad's own fixed landing gear supports startup
    # and landing anywhere; no four-post rack or exact-foot touchdown needed.
    for i,n in enumerate([75,-75],1):
        m,l=model(world,'pylon_'+str(i),(0,n,0));visual(l,'weighted_base',(0,0,.10),(.62,.62,.2),'rubber');collision(l,'weighted_base',(0,0,.10),(.62,.62,.2))
        for j in range(16):visual(l,f'stripe_{j}',(0,0,.25+j*.47),(.075 if j>0 else .11,.47),'orange' if j%2==0 else 'white','cylinder',metal=.08,rough=.5)
        collision(l,'pylon_pole',(0,0,4),(.078,8),'cylinder');scene['objects'].append(dict(type='pylon',name='pylon_'+str(i),position_enu=[0,n,0],size=[.6,.6,8],color=list(PALETTE['orange']),yaw=0))
    for target in scene['targets']:
        # Windows Ogre2 cannot render SDF polyline geometry. A closed triangulated
        # STL prism preserves exact polygon dimensions and also supports contact.
        cx,cy=target['center_enu'][:2];points=[(p[0]-cx,p[1]-cy) for p in target['vertices_enu']];mesh=Mesh()
        for i,a in enumerate(points):
            b=points[(i+1)%len(points)];p=(a[0],a[1],.022);q=(b[0],b[1],.022);aa=(a[0],a[1],0);bb=(b[0],b[1],0)
            mesh.tri((0,0,.022),p,q);mesh.tri((0,0,0),bb,aa);mesh.tri(aa,bb,q);mesh.tri(aa,q,p)
        mesh.save(ASSETS/'meshes'/(target['id']+'.stl'));uri='model://competition_assets/meshes/'+target['id']+'.stl'
        m,l=model(world,target['id']+'_mat',(cx,cy,0));visual(l,'colored_target',(0,0,0),(uri,),target['color'],'mesh',rough=.96);collision(l,'mat',(0,0,0),(uri,),'mesh',mu=.9)
    # Home yaw90 maps the left/right local mounts into ENU x offsets.
    payload(world,'red',(-23.84,0,.14));payload(world,'blue',(-24.16,0,.14))
    # Access road, concrete sidewalks, safety fencing and dense lived-in context.
    item('road','access_road',(-130,0,.01),(13,360,.025),(.10,.115,.13))
    for x in [-139,-121]:item('path','road_sidewalk_'+str(x),(x,0,.035),(3,360,.06),'concrete')
    for y in range(-175,176,10):item('road_mark','road_center_'+str(y),(-130,y,.03),(.15,4,.015),'white')
    item('road','south_road',(0,-174,.013),(360,12,.025),(.10,.115,.13))
    for x in range(-175,176,10):item('road_mark','south_center_'+str(x),(x,-174,.03),(4,.15,.015),'white')
    for x in [-108,108]:
        m,l=model(world,'safety_fence_'+str(x));
        for n in range(-160,161,8):visual(l,'post_'+str(n),(x,n,1),(.065,2),'metal','cylinder',metal=.6,rough=.48)
        for z in [.35,1.1,1.85]:beam(l,'rail_'+str(z),(x,-160,z),(x,160,z),.018,'metal')
        scene['objects'].append(dict(type='fence',name='safety_fence_'+str(x),position_enu=[x,0,1],size=[.1,320,2],color=list(PALETTE['metal']),yaw=0))
    def tree(x,y,h,i):
        m,l=model(world,'tree_'+str(i),(x,y,0));visual(l,'trunk',(0,0,h*.29),(.16,h*.58),'wood','cylinder',rough=1);collision(l,'trunk',(0,0,h*.29),(.16,h*.58),'cylinder')
        for j in range(5):
            a=j*2.399;dx=math.cos(a)*h*.17;dy=math.sin(a)*h*.17;zz=h*(.52+j*.06)
            beam(l,'branch_'+str(j),(0,0,h*.35),(dx,dy,zz),.04,'wood')
            visual(l,'foliage_'+str(j),(dx,dy,zz),('model://competition_assets/meshes/unit_sphere.stl',(h*.22,h*.19,h*.25)),(.19+j*.009,.30+j*.008,.09+j*.003),'mesh',rough=.98)
        scene['objects'].append(dict(type='tree',name='tree_'+str(i),position_enu=[x,y,0],size=[h*.7,h*.7,h],color=list(PALETTE['leaf']),yaw=0))
    tid=0
    for x in [-115,117,150,175]:
        for y in range(-147,151,23):tid+=1;tree(x+RNG.uniform(-2,2),y+RNG.uniform(-3,3),RNG.uniform(5.5,9),tid)
    for y in [-162,162]:
        for x in range(-92,95,25):tid+=1;tree(x,y,RNG.uniform(6,9),tid)
    def building(x,y,w,d,h,i):
        col=RNG.choice([(.71,.69,.62),(.72,.61,.50),(.70,.72,.70),(.56,.62,.63)]);m,l=item('building','campus_building_'+str(i),(x,y,h/2),(w,d,h),col,solid=True)
        visual(l,'pitched_roof',(0,0,h/2),('model://competition_assets/meshes/gable_roof.stl',(w+.8,d+.8,3.2)),(.25,.20,.16),'mesh',rough=.88)
        for side in [-1,1]:
            for j in range(max(2,int(w/3))):
                xx=-w/2+1.4+j*(w-2.8)/max(1,int(w/3)-1)
                for z in [-h*.15,h*.2]:
                    visual(l,f'window_{side}_{j}_{z}',(xx,side*(d/2+.018),z),(1.2,.045,1.55),'glass',metal=.6,rough=.12)
                    visual(l,f'mullion_{side}_{j}_{z}',(xx,side*(d/2+.046),z),(.045,.025,1.55),'white')
            beam(l,'gutter_'+str(side),(-w/2,side*d/2,h*.5),(w/2,side*d/2,h*.5),.065,'metal')
        visual(l,'entrance',(0,-d/2-.045,-h*.25),(1.4,.08,h*.47),'navy')
        visual(l,'AC_unit',(w/2+.3,d*.2,-h*.2),(.6,1,.75),'white',rough=.5)
    for i,(x,y,w,d,h) in enumerate([(-158,-126,19,12,6),(-159,-91,18,13,7),(-158,-53,20,14,8),(-159,42,18,14,7),(-160,83,21,14,6),(-157,128,20,15,8),(145,-125,18,13,6),(153,-66,20,14,7),(149,6,17,12,6),(151,75,21,13,7),(147,130,18,12,6)]):building(x,y,w,d,h,i)
    def car(x,y,i,yaw=math.pi/2):
        col=RNG.choice([(.76,.77,.75),(.12,.16,.20),(.48,.08,.08),(.10,.23,.40)]);m,l=model(world,'parked_vehicle_'+str(i),(x,y,0),yaw)
        visual(l,'painted_body',(0,0,0),('model://competition_assets/meshes/car_body.stl',),col,'mesh',metal=.45,rough=.23);collision(l,'car_collision',(0,0,.8),(4.3,1.8,1.3))
        for xx in [-1.3,1.25]:
            for yy in [-.87,.87]:
                visual(l,f'tire_{xx}_{yy}',(xx,yy,.43),(.33,.20),'rubber','cylinder',(math.pi/2,0,0),rough=.9)
                visual(l,f'rim_{xx}_{yy}',(xx,yy*1.13,.43),(.19,.015),'metal','cylinder',(math.pi/2,0,0),metal=.8,rough=.18)
        for yy in [-.755,.755]:visual(l,'side_window_'+str(yy),(.24,yy,1.21),(1.34,.025,.38),'glass',metal=.65,rough=.09)
        visual(l,'windscreen',(-.54,0,1.2),(.035,1.42,.55),'glass',rpy=(0,-.55,0),metal=.65,rough=.1)
        for yy in [-.55,.55]:
            visual(l,'headlamp_'+str(yy),(-2.1,yy,.73),(.04,.30,.15),'ivory',metal=.6,rough=.08);visual(l,'taillamp_'+str(yy),(2.11,yy,.72),(.04,.25,.16),'red',rough=.12)
        scene['objects'].append(dict(type='vehicle',name='parked_vehicle_'+str(i),position_enu=[x,y,0],size=[4.3,1.8,1.6],color=list(col),yaw=yaw))
    item('parking','asphalt_parking',(-154,-5,.014),(25,49,.026),(.13,.14,.15))
    for i,y in enumerate(range(-22,23,5)):
        item('parking_mark','parking_bay_'+str(i),(-154,y,.036),(9,.09,.015),'white');car(-154,y+2,i,0)
    for i,y in enumerate([-132,-98,-67,45,80,132],10):car(-122.8,y,i)
    # Tents, flight desk, benches, signs, bins and barriers make the operations area
    # readable from the map and detailed in the actual onboard camera.
    for i,(x,y) in enumerate([(-91,-26),(-91,-13),(-91,0),(-91,13),(-91,26)]):
        m,l=item('tent','team_tent_'+str(i),(x,y,2.5),(7,7,.2),'white')
        visual(l,'canvas_roof',(0,0,.1),('model://competition_assets/meshes/gable_roof.stl',(7.5,7.5,2)),(.84,.84,.78),'mesh',rough=.92)
        for xx in [-3.2,3.2]:
            for yy in [-3.2,3.2]:beam(l,f'leg_{xx}_{yy}',(xx,yy,-2.5),(xx,yy,0),.04,'metal')
        visual(l,'folding_table',(0,0,-1.65),(3,.85,.08),'metal',metal=.35)
        visual(l,'equipment_case',(.6,0,-1.43),(.8,.5,.35),'navy')
    for i,y in enumerate(range(-48,49,12)):
        m,l=item('bench','spectator_bench_'+str(i),(-101,y,.55),(2,.55,.12),'wood',solid=True)
        visual(l,'backrest',(0,.25,.35),(2,.08,.55),'wood');
        for xx in [-.75,.75]:visual(l,'leg_'+str(xx),(xx,0,-.24),(.1,.4,.5),'metal')
    for i,y in enumerate(range(-50,51,10)):
        m,l=model(world,'traffic_cone_'+str(i),(-112,y,.0));visual(l,'rubber_foot',(0,0,.025),(.4,.4,.05),'rubber')
        for j,(r,h) in enumerate([(.15,.2),(.105,.17),(.06,.14)]):visual(l,'stripe_'+str(j),(0,0,.10+j*.14),(r,h),'orange' if j%2==0 else 'white','cylinder')
    for i,y in enumerate([-42,42]):
        m,l=item('sign','field_sign_'+str(i),(-104,y,1.35),(1.8,.10,.85),'navy');beam(l,'post',(0,0,-1.35),(0,0,0),.05,'metal')
        for j in range(3):visual(l,'reflective_line_'+str(j),(-.45+j*.45,-.06,0),(.2,.02,.55),'white')
    for i,(x,y) in enumerate([(-91,-43),(-91,43),(102,-90),(102,90)]):
        m,l=item('bin','waste_bin_'+str(i),(x,y,.5),(.55,.55,1),(.10,.28,.20),solid=True);visual(l,'lid',(0,0,.52),(.65,.65,.08),'navy')
    # Soft low hills make the real camera horizon read as a landscape.
    for i in range(18):
        a=i*2*math.pi/18;r=RNG.uniform(480,660);h=RNG.uniform(20,48);m,l=model(world,'distant_hill_'+str(i),(r*math.cos(a),r*math.sin(a),-h*.38));visual(l,'hill',(0,0,0),('model://competition_assets/meshes/unit_sphere.stl',(RNG.uniform(90,160),RNG.uniform(80,150),h)),(.30,.39,.23),'mesh',rough=1)
    quad=drone(source);world.append(quad)
    observer,ol=model(world,'map_observer',(0,0,271.36),math.pi/2);sen=sub(ol,'sensor',name='overview_camera',type='camera');pose(sen,(0,0,0),(0,math.pi/2,0));sub(sen,'always_on','true');sub(sen,'update_rate',1);sub(sen,'topic','/course/realistic/overview/image');ca=sub(sen,'camera');sub(ca,'horizontal_fov',math.radians(70));im=sub(ca,'image');sub(im,'width',1400);sub(im,'height',1400);sub(im,'format','R8G8B8');cl=sub(ca,'clip');sub(cl,'near',.1);sub(cl,'far',900)
    # A separate massless spectator sensor follows the actual physics body.
    # Its optical +X axis is aimed by PayloadMechanics; neither onboard vision
    # nor the fixed north-up map consumes this image.
    follow,fl=model(world,'follow_observer',(-27,-3,2.0));sen=sub(fl,'sensor',name='follow_camera',type='camera');pose(sen);sub(sen,'always_on','true');sub(sen,'update_rate',8);sub(sen,'topic','/course/realistic/follow/image');ca=sub(sen,'camera');sub(ca,'horizontal_fov',math.radians(70));im=sub(ca,'image');sub(im,'width',640);sub(im,'height',360);sub(im,'format','R8G8B8');cl=sub(ca,'clip');sub(cl,'near',.06);sub(cl,'far',650)
    if plugin_path:
        pp=Path(plugin_path)
        if pp.is_file():physics_plugin=pp.resolve().as_posix()
        else:
            dll=next(iter(pp.rglob('PayloadMechanics.dll')),None) if pp.exists() else None
            if dll:physics_plugin=dll.resolve().as_posix()
    plugin=sub(world,'plugin',filename=physics_plugin,name='uav_course::PayloadMechanics');sub(plugin,'vehicle','competition_quad');sub(plugin,'body_link','iris_with_standoffs::base_link');sub(plugin,'payload_link','payload_link');sub(plugin,'initial_closed','true');sub(plugin,'capture_radius',.16);sub(plugin,'camera_pose','.38 0 -.13 0 1.5707963267948966 0')
    sub(plugin,'follow_model','follow_observer')
    scene['overview']['image_px']=[1400,1400];scene['overview']['pose_enu_rpy']=[0,0,271.36,0,math.pi/2,math.pi/2];scene['map_view_bounds']={'east_min':-190,'east_max':190,'north_min':-190,'north_max':190}
    scene['camera']['local_pose']=[.38,0,-.13,0,math.pi/2,0];scene['camera']['hfov_rad']=math.pi/2;scene['camera']['update_rate_hz']=8
    scene['follow_camera']={'model':'follow_observer','topic':'/course/realistic/follow/image','image_px':[640,360],'hfov_rad':math.radians(70),'update_rate_hz':8,'default_mode':'chase','purpose':'external spectator only; not onboard perception'}
    scene['landing_gear']={'foot_bottom_body_z_m':-.845,'foot_radius_m':.014,'strut_radius_m':.007,'foot_centres_body_xyz':[[math.copysign(.48,x),math.copysign(.48,y),-.831] for x,y in [(.123,.22),(.123,-.22),(-.14,.21),(-.14,-.21)]],'design':'four fixed splayed carbon struts, rounded toes, no horizontal bars','lumped_in_existing_body_mass':True,'home_pad_top_m':.0275,'nominal_rest_body_z_m':.8725,'nominal_loaded_cube_pad_clearance_m':.005,'pickup_body_z_m':.89,'pickup_foot_mat_clearance_m':.023}
    # Resolve all resources for standalone native Windows launches. The source
    # models remain portable model:// URIs for installing into another checkout.
    for tag in ('uri','albedo_map','normal_map','roughness_map'):
        for el in world.findall('.//'+tag):
            value=el.text or ''
            if value.startswith('model://'):
                rel=value[8:];candidates=[ROOT/'models'/rel,source/'models'/rel]
                found=next((p for p in candidates if p.is_file()),None)
                if found is None and rel.endswith('grass_albedo.png'):
                    # A generated photoreal tile is supplied before final QA.
                    continue
                if found is None:raise FileNotFoundError(value)
                el.text=found.resolve().as_posix()
    out=Path(out or ROOT/'world/competition.sdf');out.parent.mkdir(parents=True,exist_ok=True);E.indent(root,space='  ');E.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
    SCENE.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'world':str(out),'models':len(world.findall('model')),'visuals':len(world.findall('.//visual')),'collisions':len(world.findall('.//collision')),'dynamic_payloads':2,'payload_mass_kg':.3,'home_distance_to_centre_m':24,'pylon_spacing_m':150,'objects':len(scene['objects']),'asset_triangles':'Procedural code-owned STL meshes + native Iris meshes','upstream_flight_dynamics':'ArduPilot/ardupilot_gazebo Iris, unchanged native motor/IMU joints','textures':'Generated photoreal grass albedo, with prompt provenance'}
    (ROOT/'world/world_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--source',type=Path);p.add_argument('--plugin-path',type=Path);p.add_argument('--seed',type=int,default=2026);p.add_argument('--physics-plugin',default='PayloadMechanics');a=p.parse_args();generate(a.out,a.source,a.plugin_path,a.seed,a.physics_plugin)
