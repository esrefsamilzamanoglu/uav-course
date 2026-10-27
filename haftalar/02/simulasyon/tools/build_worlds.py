"""Deterministic course scenery and portable SDF worlds; no flight control."""
from __future__ import annotations
import argparse, copy, importlib.util, json, math, random, struct
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'models/course_assets'
COLORS={'leaf':(.18,.36,.12),'leaf_light':(.32,.48,.17),'bark':(.29,.20,.13),
        'crop':(.29,.48,.14),'crop_light':(.43,.57,.22),'red':(.55,.18,.13),
        'roof':(.24,.26,.28),'concrete':(.69,.67,.58),'black':(.055,.065,.07),
        'glass':(.15,.35,.43),'white':(.88,.88,.81),'yellow':(.91,.65,.12)}

def sub(parent,tag,text=None,**attrs):
    node=E.SubElement(parent,tag,attrs)
    if text is not None:node.text=str(text)
    return node
def vector(v):return ' '.join(f'{n:.7g}' for n in v)
def mat(parent,color,texture=None):
    m=sub(parent,'material');c=vector(tuple(color)+(1,))
    sub(m,'ambient',c);sub(m,'diffuse',c);sub(m,'specular','0.06 0.06 0.06 1')
    if texture:
        metal=sub(sub(m,'pbr'),'metal');sub(metal,'albedo_map',texture)
        sub(metal,'roughness',.88);sub(metal,'metalness',0)
def visual(link,name,pos,size,color,shape='box',rpy=(0,0,0),texture=None):
    v=sub(link,'visual',name=name);sub(v,'pose',vector(tuple(pos)+tuple(rpy)))
    g=sub(v,'geometry');geo=sub(g,shape)
    if shape=='box':sub(geo,'size',vector(size))
    elif shape=='sphere':sub(geo,'radius',size[0])
    elif shape=='cylinder':sub(geo,'radius',size[0]);sub(geo,'length',size[1])
    elif shape=='plane':sub(geo,'normal','0 0 1');sub(geo,'size',vector(size))
    mat(v,color,texture)
    return v
def model(world,name,pos=(0,0,0),yaw=0):
    m=sub(world,'model',name=name);sub(m,'static','true');sub(m,'pose',vector(tuple(pos)+(0,0,yaw)))
    return m,sub(m,'link',name='body')
def solid_box(world,name,pos,size,color,yaw=0,collision=True):
    m,l=model(world,name,pos,yaw);visual(l,'body',(0,0,0),size,color)
    if collision:sub(sub(sub(l,'collision',name='solid'),'geometry'),'box').append(E.fromstring('<size>'+vector(size)+'</size>'))
    return m,l

class Mesh:
    def __init__(self):self.parts={}
    def tri(self,c,a,b,d):self.parts.setdefault(c,[]).extend((a,b,d))
    def box(self,pos,size,c):
        x,y,z=pos;dx,dy,dz=[v/2 for v in size]
        p=[(x+a*dx,y+b*dy,z+v*dz) for a,b,v in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        for a,b,d,e in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.tri(c,p[a],p[b],p[d]);self.tri(c,p[a],p[d],p[e])
    def cone(self,pos,r,h,c,sides=8):
        x,y,z=pos;top=(x,y,z+h)
        for i in range(sides):
            a=2*math.pi*i/sides;b=2*math.pi*(i+1)/sides
            self.tri(c,(x+r*math.cos(a),y+r*math.sin(a),z),(x+r*math.cos(b),y+r*math.sin(b),z),top)
    def plant(self,x,y,h):
        self.box((x,y,h/2),(.035,.035,h),'crop')
        for j in range(6):
            a=j*2.399963;r=.35+.035*j;z=.10+j*.075
            along=np.array([math.cos(a),math.sin(a),0]);across=np.array([-math.sin(a),math.cos(a),0])
            base=np.array([x,y,z]);tip=base+along*r+np.array([0,0,.08]);spine=base+along*r*.5+np.array([0,0,.18])
            left=spine+across*.085;right=spine-across*.085
            color='crop' if j%2 else 'crop_light'
            for p,q,t in [(base,left,spine),(base,spine,right),(left,tip,spine),(spine,tip,right)]:
                self.tri(color,tuple(p),tuple(q),tuple(t));self.tri(color,tuple(t),tuple(q),tuple(p))
    def write(self,path):
        d=E.Element('COLLADA',xmlns='http://www.collada.org/2005/11/COLLADASchema',version='1.4.1')
        a=sub(d,'asset');sub(a,'created','2026-10-27T00:00:00Z');sub(a,'modified','2026-10-27T00:00:00Z');sub(a,'unit',name='meter',meter='1');sub(a,'up_axis','Z_UP')
        effects=sub(d,'library_effects');materials=sub(d,'library_materials');geos=sub(d,'library_geometries');scenes=sub(d,'library_visual_scenes');scene=sub(scenes,'visual_scene',id='Scene',name='Scene')
        for name,vertices in self.parts.items():
            color=COLORS[name]
            effect=sub(effects,'effect',id=name+'-fx');lambert=sub(sub(sub(effect,'profile_COMMON'),'technique',sid='common'),'lambert');sub(sub(lambert,'diffuse'),'color',vector(color+(1,)))
            sub(sub(materials,'material',id=name+'-mat',name=name),'instance_effect',url='#'+name+'-fx')
            mesh=sub(sub(geos,'geometry',id=name+'-geo',name=name),'mesh')
            src=sub(mesh,'source',id=name+'-pos');sub(src,'float_array',vector([q for p in vertices for q in p]),id=name+'-arr',count=str(len(vertices)*3))
            access=sub(sub(src,'technique_common'),'accessor',source='#'+name+'-arr',count=str(len(vertices)),stride='3')
            for axis in 'XYZ':sub(access,'param',name=axis,type='float')
            ve=sub(mesh,'vertices',id=name+'-verts');sub(ve,'input',semantic='POSITION',source='#'+name+'-pos')
            tri=sub(mesh,'triangles',count=str(len(vertices)//3),material=name+'-symbol');sub(tri,'input',semantic='VERTEX',source='#'+name+'-verts',offset='0');sub(tri,'p',' '.join(map(str,range(len(vertices)))))
            node=sub(scene,'node',id=name+'-node');inst=sub(node,'instance_geometry',url='#'+name+'-geo');binding=sub(sub(inst,'bind_material'),'technique_common');sub(binding,'instance_material',symbol=name+'-symbol',target='#'+name+'-mat')
        sub(sub(d,'scene'),'instance_visual_scene',url='#Scene');path.parent.mkdir(parents=True,exist_ok=True);E.ElementTree(d).write(path,encoding='utf-8',xml_declaration=True)
        # Explicit per-visual SDF materials also work with the Windows Ogre2 loader.
        for name in self.parts:
            part=copy.deepcopy(d)
            for container_tag,child_tag,suffix in [('library_geometries','geometry','-geo'),('library_effects','effect','-fx'),('library_materials','material','-mat')]:
                container=part.find(container_tag)
                for child in list(container):
                    if child.get('id')!=name+suffix:container.remove(child)
            vs=part.find('library_visual_scenes/visual_scene')
            for child in list(vs):
                if child.get('id')!=name+'-node':vs.remove(child)
            E.ElementTree(part).write(path.with_name(path.stem+'_'+name+'.dae'),encoding='utf-8',xml_declaration=True)
        path.with_suffix('.materials.json').write_text(json.dumps(list(self.parts)))
        for name,vertices in self.parts.items():
            with path.with_name(path.stem+'_'+name+'.stl').open('wb') as stream:
                stream.write(b'UAV Course week2 generated geometry'.ljust(80,b'\0'));stream.write(struct.pack('<I',len(vertices)//3))
                for i in range(0,len(vertices),3):
                    a,b,c=[np.array(p,dtype=float) for p in vertices[i:i+3]];normal=np.cross(b-a,c-a);norm=np.linalg.norm(normal)
                    if norm:normal/=norm
                    stream.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
def mesh_model(w,name,file):
    m,l=model(w,name)
    stem=Path(file).stem
    for color in json.loads((ASSETS/'meshes'/file).with_suffix('.materials.json').read_text()):
        v=sub(l,'visual',name=color);sub(sub(sub(v,'geometry'),'mesh'),'uri',f'model://course_assets/meshes/{stem}_{color}.stl');mat(v,COLORS[color])
    return m

def terrain(kind):
    rng=np.random.default_rng(2302);n=2048
    base=np.array([101,120,74] if kind!='building' else [114,127,103],dtype=float)
    noise=rng.normal(0,3,(n,n,1));arr=np.clip(base+noise,0,255).astype(np.uint8)
    im=Image.fromarray(arr);draw=ImageDraw.Draw(im)
    extent=450 if kind=='rural' else 150
    def rect(x0,y0,x1,y1,c):draw.rectangle(((x0+extent)*n/(2*extent),(extent-y1)*n/(2*extent),(x1+extent)*n/(2*extent),(extent-y0)*n/(2*extent)),fill=c)
    if kind=='farm':
        rect(-33,17,33,68,(105,75,44))
        for x in np.arange(-31,32,1.4):rect(x,18,x+.65,67,(66+int((x+31)%7),103,41))
        rect(-60,-15,80,-5,(137,124,99));rect(45,-10,52,95,(137,124,99))
        rect(-85,78,-40,120,(173,155,78));rect(60,23,110,85,(81,112,46));rect(-105,-60,-40,7,(107,84,55))
    elif kind=='building':
        rect(-30,15,30,75,(158,157,148));rect(-80,-12,85,0,(64,70,71));rect(37,-80,47,90,(64,70,71))
        for y in range(-70,90,12):rect(41.5,y,42.0,y+5,(228,220,170))
        for x in range(-70,85,12):rect(x,-6.2,x+5,-5.8,(228,220,170))
        for x in range(-25,26,6):rect(x,6,x+.14,14,(230,229,208))
    else:
        rect(-9,-250,9,350,(73,77,75))
        for y in range(-235,345,20):rect(-.4,y,.4,y+9,(239,235,207))
        for side in (-7.8,7.8):rect(side,-240,side+.15,340,(238,232,206))
        rect(-90,90,100,370,(132,144,92))
        rect(-180,0,-150,390,(120,101,73));rect(140,100,380,320,(91,121,60))
        rect(-400,-50,400,-39,(137,122,95))
    # Ground texture is generated from geometry coordinates, not a substitute for camera images.
    grain=rng.normal(0,3.5,(n,n,1));im=Image.fromarray(np.clip(np.asarray(im,dtype=float)+grain,0,255).astype(np.uint8))
    path=ASSETS/'textures'/f'{kind}_ground.png';path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
    return extent

def tree(mesh,x,y,scale=1):
    mesh.box((x,y,1.2*scale),(.35*scale,.35*scale,2.4*scale),'bark')
    mesh.cone((x,y,1.1*scale),1.8*scale,3.3*scale,'leaf')
    mesh.cone((x,y,2.3*scale),1.35*scale,2.7*scale,'leaf_light')
def camera(w,name,pos,target,topic,width=1280,height=800,rate=1,fov=1.22173):
    dx,dy,dz=[b-a for a,b in zip(pos,target)];yaw=math.atan2(dy,dx);pitch=math.atan2(-dz,math.hypot(dx,dy))
    m,l=model(w,name,pos);m.find('pose').text=vector(tuple(pos)+(0,pitch,yaw))
    sensor=sub(l,'sensor',name='rgb',type='camera');sub(sensor,'always_on','true');sub(sensor,'update_rate',rate);sub(sensor,'topic',topic)
    cam=sub(sensor,'camera');sub(cam,'horizontal_fov',fov);img=sub(cam,'image');sub(img,'width',width);sub(img,'height',height);sub(img,'format','R8G8B8');clip=sub(cam,'clip');sub(clip,'near',.05);sub(clip,'far',1200)
    return m,l
def world(name,kind,vehicle,upstream):
    sdf=E.Element('sdf',version='1.9');w=sub(sdf,'world',name=name)
    ph=sub(w,'physics',name='1ms',type='ignore');sub(ph,'max_step_size',.001);sub(ph,'real_time_factor',1)
    for filename,system in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('imu','Imu'),('navsat','NavSat')]:sub(w,'plugin',filename=f'gz-sim-{filename}-system',name='gz::sim::systems::'+system)
    sensors=sub(w,'plugin',filename='gz-sim-sensors-system',name='gz::sim::systems::Sensors');sub(sensors,'render_engine','ogre2')
    scene=sub(w,'scene');sub(scene,'ambient','0.55 0.58 0.61 1');sub(scene,'background','0.64 0.77 0.88 1');sub(scene,'shadows','true');sub(scene,'sky')
    spherical=sub(w,'spherical_coordinates')
    for tag,value in [('latitude_deg',-35.363262),('longitude_deg',149.165237),('elevation',584),('heading_deg',0),('surface_model','EARTH_WGS84')]:sub(spherical,tag,value)
    light=sub(w,'light',name='afternoon_sun',type='directional');sub(light,'pose','0 0 200 0 0 0');sub(light,'cast_shadows','true');sub(light,'diffuse','.88 .85 .77 1');sub(light,'specular','.18 .18 .18 1');sub(light,'direction','-.35 -.42 -.84')
    extent=terrain(kind)
    _,far=model(w,'horizon_ground',(0,0,-.03));visual(far,'grass',(0,0,0),(2400,2400),(.37,.44,.27),'plane')
    plane=sub(sub(sub(far,'collision',name='continuous_ground'),'geometry'),'plane');sub(plane,'normal','0 0 1');sub(plane,'size','2400 2400')
    ground,link=solid_box(w,'ground',(0,0,-.5),(extent*2,extent*2,1),(.4,.45,.3))
    link.remove(link.find('visual'));visual(link,'ground_surface',(0,0,.501),(extent*2,extent*2),(1,1,1),'plane',texture=f'model://course_assets/textures/{kind}_ground.png')
    source=upstream/'models'/vehicle/'model.sdf';v=copy.deepcopy(E.parse(source).getroot().find('model'))
    # Reuse the exact upstream flight dynamics, not a scripted UAV animation.
    helper=ROOT.parents[2]/'windows/resolve_world.py'
    spec=importlib.util.spec_from_file_location('week1_resolver',helper);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.Resolver(upstream/'models').expand(v)
    v.insert(0,E.fromstring('<pose degrees="true">0 0 '+('0.195 0 0 90' if kind!='rural' else '0.43 0 0 180')+'</pose>'))
    if kind=='rural':
        wing=v.find("./model[@name='zephyr']/link[@name='wing']")
        for i,(x,y) in enumerate([(-.45,-.18),(.45,-.18),(0,.55)]):
            visual(wing,'course_wheel_'+str(i),(x,y,-.28),(.09,),(.06,.065,.07),'sphere')
            collision=sub(wing,'collision',name='course_wheel_'+str(i));sub(collision,'pose',vector((x,y,-.28,0,0,0)))
            sub(sub(sub(collision,'geometry'),'sphere'),'radius',.09)
            ode=sub(sub(sub(collision,'surface'),'friction'),'ode');sub(ode,'mu',.04);sub(ode,'mu2',.04)
    plugin=v.find("./plugin[@name='ArduPilotPlugin']")
    if plugin is None:raise RuntimeError('Missing original flight dynamics plugin')
    for channel,topic,mult,offset in [(8,'roll',math.pi/3,-.5),(9,'pitch',-math.pi/2,-1),(10,'yaw',-2*math.pi,-.5),(11,'pump',1,0)]:
        control=sub(plugin,'control',channel=str(channel));sub(control,'jointName','zephyr::propeller_joint' if kind=='rural' else 'iris_with_standoffs::rotor_0_joint')
        sub(control,'type','COMMAND');sub(control,'multiplier',mult);sub(control,'offset',offset);sub(control,'servo_min',1000);sub(control,'servo_max',2000)
        sub(control,'cmd_topic','/course/pump' if topic=='pump' else '/course/gimbal/'+topic)
    w.append(v)
    cs=sub(w,'plugin',filename='CourseScene',name='uav_course::CourseScene');sub(cs,'vehicle',vehicle);sub(cs,'rural',str(kind=='rural').lower())
    if kind=='rural':sub(cs,'camera_yaw_offset',-math.pi/2)
    camera(w,'course_camera',(0,0,.1),(0,0,-1),'/course/camera/image',1280 if kind=='rural' else 960,800 if kind=='rural' else 640,6,1.22173)
    if kind=='farm':camera(w,'overview',(73,-45,76),(0,38,0),'/course/overview/image',1600,1000,1,1.1)
    elif kind=='building':camera(w,'overview',(75,-30,60),(0,45,7),'/course/overview/image',1600,1000,1,1.0)
    else:camera(w,'overview',(320,-250,310),(0,170,0),'/course/overview/image',1600,1000,.5,1.1)
    return sdf,w

def make_farm(w):
    mesh=Mesh();rng=random.Random(2302)
    for x in np.arange(-31,32,1.4):
        for y in np.arange(19,67,1.4):
            mesh.plant(x+rng.uniform(-.08,.08),y,rng.uniform(.5,.75))
    for x,y in [(-55,-35),(-70,-30),(-78,10),(75,15),(78,80),(90,110),(-78,75),(-88,110)]:tree(mesh,x,y,rng.uniform(.9,1.8))
    for x in range(-35,36,5):mesh.box((x,73,.65),(.13,.13,1.3),'bark')
    mesh.box((0,73,.8),(70,.10,.10),'bark');mesh.box((0,73,.4),(70,.10,.10),'bark')
    # Barn with a proper pitched roof.
    mesh.box((-60,38,2),(12,9,4),'red')
    for i in range(9):mesh.box((-65.5+i*1.4,33.45,2),(.06,.08,4),'white')
    for y0,y1,z0,z1 in [(33.5,38,4,6.1),(38,42.5,6.1,4)]:
        for a,b,c in [((-66,y0,z0),(-54,y0,z0),(-54,y1,z1)),((-66,y0,z0),(-54,y1,z1),(-66,y1,z1))]:mesh.tri('roof',a,b,c)
    mesh.box((-60,33.43,1.4),(3,.12,2.8),'roof');mesh.box((-60,33.35,1.4),(.08,.05,2.8),'white')
    # Tractor, frame, bonnet, cab and four tires.
    mesh.box((-49,20,.65),(3.8,1.8,.7),'leaf_light');mesh.box((-48.0,20,1.45),(1.2,1.65,1.25),'glass');mesh.box((-48,20,2.12),(1.5,1.9,.13),'yellow')
    for x in (-50.3,-47.8):
        for y in (18.95,21.05):mesh.box((x,y,.53),(.8,.45,1.05),'black')
    mesh.write(ASSETS/'meshes/farm_details.dae');mesh_model(w,'farm_details','farm_details.dae')
    m,l=model(w,'water_tank',(-69,19,1.6));visual(l,'tank',(0,0,0),(2,3.2),(.65,.69,.72),'cylinder');visual(l,'top',(0,0,1.6),(2.05,.15),(.35,.39,.4),'cylinder')
    m,l=model(w,'spray_cloud',(0,0,-12))
    for i in range(18):
        a=i*2.399;radius=.4+.075*i
        v=visual(l,'drop_'+str(i),(math.cos(a)*radius,math.sin(a)*radius,-.035*i),(.075,),(.74,.87,.91),'sphere');sub(v,'transparency',.3)
    # Physical takeoff pad; no visual grid laid over the survey images.
    m,l=solid_box(w,'launch_pad',(0,0,.015),(4,4,.03),(.22,.25,.26))
    for x in (-1.4,1.4):visual(l,'stripe'+str(x),(x,0,.021),(.10,3,.01),(.91,.72,.15))

def facade_texture(side):
    rng=random.Random(800+side);im=Image.new('RGB',(1536,1536),(177+side*4,171,151));d=ImageDraw.Draw(im)
    for y in range(0,1536,34):
        d.line((0,y,1536,y),fill=(144,143,131),width=2)
        for x in range((y//34%2)*32,1536,64):d.line((x,y,x,y+34),fill=(155,153,138),width=1)
    for row in range(3):
        for col in range(4):
            x=110+col*360;y=145+row*400
            d.rectangle((x-13,y-13,x+213,y+273),fill=(221,219,195));d.rectangle((x,y,x+200,y+260),fill=(48+rng.randrange(20),88+rng.randrange(20),103+rng.randrange(30)))
            d.line((x+100,y,x+100,y+260),fill=(177,185,176),width=8);d.line((x,y+130,x+200,y+130),fill=(177,185,176),width=8)
            d.polygon([(x+5,y+5),(x+150,y+5),(x+5,y+180)],fill=(111,143,149))
            d.rectangle((x-20,y+270,x+220,y+285),fill=(126,125,113))
            # Unique facade patches remove the repeated-window ambiguity.
            for j in range(5):
                xx=x+rng.randrange(180);yy=y+300+rng.randrange(50);d.rectangle((xx,yy,xx+rng.randrange(8,30),yy+8),fill=(115+rng.randrange(80),105+rng.randrange(60),85+rng.randrange(70)))
    im.save(ASSETS/'textures'/f'facade_{side}.png')

def make_building(w):
    m,l=solid_box(w,'mapping_building',(0,45,7),(14,12,14),(.7,.67,.58))
    for side in range(4):
        facade_texture(side)
        # Planes face outwards: textured real wall surfaces, not slide artwork.
        if side==0:pos=(0,-6.012,0);rpy=(math.pi/2,0,0);size=(14,14)
        elif side==1:pos=(7.012,0,0);rpy=(math.pi/2,0,math.pi/2);size=(12,14)
        elif side==2:pos=(0,6.012,0);rpy=(math.pi/2,0,math.pi);size=(14,14)
        else:pos=(-7.012,0,0);rpy=(math.pi/2,0,-math.pi/2);size=(12,14)
        visual(l,'facade_'+str(side),pos,size,(1,1,1),'plane',rpy,texture=f'model://course_assets/textures/facade_{side}.png')
    visual(l,'roof',(0,0,7.1),(14.6,12.6,.25),(.25,.28,.3));visual(l,'entry',(0,-6.07,-5.5),(2.8,.16,3),(.28,.17,.12))
    visual(l,'canopy',(0,-7.3,-3.8),(4,2.8,.18),(.79,.78,.7))
    for x in (-2,2):visual(l,'pillar'+str(x),(x,-8,-5.3),(.18,.18,3.2),(.71,.71,.65))
    for x in (-4,0,4):visual(l,'solar'+str(x),(x,1,7.45),(3,5,.15),(.10,.19,.26),rpy=(.12,0,0))
    visual(l,'vent',(3,-3.5,7.7),(1.5,1.2,1.2),(.55,.59,.57))
    mesh=Mesh();rng=random.Random(44)
    for x,y in [(-43,40),(-40,85),(35,87),(65,50),(-55,-35),(60,-30)]:tree(mesh,x,y,rng.uniform(1.1,1.7))
    for i,c in enumerate(('red','white','glass')):
        x=-18+i*6;mesh.box((x,10,.7),(2.1,4.2,1.3),c);mesh.box((x,10.4,1.5),(1.8,2.1,.8),'glass')
        for xx in (x-1,x+1):
            for yy in (8.6,11.4):mesh.box((xx,yy,.4),(.35,.7,.8),'black')
    for x,y in [(-55,90),(63,91)]:mesh.box((x,y,3),(13,10,6),'concrete');mesh.box((x,y,6.2),(14,11,.3),'roof')
    mesh.write(ASSETS/'meshes/building_details.dae');mesh_model(w,'building_details','building_details.dae')

def make_rural(w):
    mesh=Mesh();rng=random.Random(91)
    for i in range(85):
        x=rng.choice([-1,1])*rng.uniform(120,410);y=rng.uniform(-210,420);tree(mesh,x,y,rng.uniform(1.0,2.7))
    for x,y in [(-120,80),(120,180),(155,340),(-135,280)]:
        mesh.box((x,y,2.2),(14,9,4.4),'concrete')
        for y0,y1,z0,z1 in [(y-5,y,4.4,6.5),(y,y+5,6.5,4.4)]:
            mesh.tri('red',(x-7.5,y0,z0),(x+7.5,y0,z0),(x+7.5,y1,z1));mesh.tri('red',(x-7.5,y0,z0),(x+7.5,y1,z1),(x-7.5,y1,z1))
    # Four low rolling hills outside the runway and scan corridor.
    for x,y in [(-330,-40),(340,190),(-300,380),(310,420)]:mesh.cone((x,y,0),rng.uniform(80,130),rng.uniform(18,40),'leaf_light',24)
    mesh.write(ASSETS/'meshes/rural_details.dae');mesh_model(w,'rural_details','rural_details.dae')
    for i in range(3):
        m,l=model(w,'walker_'+str(i+1),(-30+35*i,150+70*i,0))
        shirt=[(.85,.20,.08),(.10,.24,.72),(.88,.65,.08)][i]
        visual(l,'torso',(0,0,1.12),(.40,.28,.63),shirt);visual(l,'head',(0,0,1.61),(.16,),(.68,.45,.28),'sphere')
        for sign in (-1,1):
            visual(l,'leg'+str(sign),(.035*sign,.115*sign,.43),(.15,.15,.78),(.11,.14,.18),rpy=(0,sign*.12,0))
            visual(l,'arm'+str(sign),(.045*sign,.27*sign,1.05),(.12,.12,.65),shirt,rpy=(sign*.13,sign*.18,0))
            visual(l,'shoe'+str(sign),(.09,.115*sign,.06),(.27,.16,.12),(.04,.045,.05))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--upstream',type=Path,required=True);args=ap.parse_args()
    (ROOT/'worlds').mkdir(exist_ok=True);(ASSETS/'textures').mkdir(parents=True,exist_ok=True)
    for kind,name,vehicle,fn in [('farm','course_farm','iris_with_ardupilot',make_farm),('building','course_building','iris_with_ardupilot',make_building),('rural','course_rural','zephyr_with_ardupilot',make_rural)]:
        sdf,w=world(name,kind,vehicle,args.upstream);fn(w);E.indent(sdf,space='  ')
        dest=ROOT/'worlds'/f'{kind}.sdf';E.ElementTree(sdf).write(dest,encoding='utf-8',xml_declaration=True)
        print(json.dumps({'world':str(dest),'models':len(w.findall('model')),'visuals':len(w.findall('.//visual'))}),flush=True)
if __name__=='__main__':main()
