"""Draw teaching figures from geometry and real recordings, never fake sim views."""
from pathlib import Path
import os,sys,json,math,hashlib
os.environ.setdefault('OMP_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'simulasyon/tools'))
import vision_bootstrap
import numpy as np
from PIL import Image
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,Ellipse,Polygon,FancyArrowPatch,Rectangle,Circle
from scipy.spatial.transform import Rotation
from vision_geometry import geometry,load_frames
A=ROOT/'sunum/gorseller';V=ROOT/'sunum/semalar';V.mkdir(exist_ok=True)
BG='#edf3ff';NAVY='#18365d';TEAL='#238b88';GOLD='#d79a29';INK='#263d56';RED='#b74a47';BLUE='#568ed0';WHITE='#ffffff'
plt.rcParams.update({'font.family':'Century Gothic','font.size':18,'text.color':INK,'axes.labelcolor':INK,'axes.edgecolor':NAVY,'savefig.facecolor':BG})
manifest=[]
def canvas():
    fig,ax=plt.subplots(figsize=(16,6.6),facecolor=BG);fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,16),ylim=(0,8.2));ax.axis('off');return fig,ax
def label(ax,x,y,t,size=22,c=INK,weight='normal',ha='left',va='center',**kw):return ax.text(x,y,t,fontsize=size*1.15,color=c,fontweight=weight,ha=ha,va=va,**kw)
def box(ax,x,y,w,h,title,body='',color=WHITE):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=.16',facecolor=color,edgecolor='none'))
    label(ax,x+.22,y+h-.47,title,23,NAVY,'bold')
    if body:label(ax,x+.22,y+h-.95,body,18,va='top',linespacing=1.55)
def arrow(ax,a,b,c=TEAL,rad=0,lw=3):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=22,linewidth=lw,color=c,connectionstyle=f'arc3,rad={rad}'))
def image(ax,name,extent):
    im=Image.open(A/name)
    ax.imshow(im,extent=extent,zorder=1,**({'cmap':'gray','vmin':0,'vmax':255} if im.mode in ('L','1') else {}))
def save(fig,name,description,sources=()):
    fig.savefig(A/(name+'.png'),dpi=125);fig.savefig(V/(name+'.svg'));plt.close(fig)
    manifest.append({'file':name+'.png','kind':'teaching diagram / measured-data visualization','description':description,'source_files':list(sources),'sha256':hashlib.sha256((A/(name+'.png')).read_bytes()).hexdigest()})

def system():
    fig,ax=canvas();box(ax,.7,4.3,4.1,2.8,'Mission Planner','Görevi yükle\nAUTO → ARM')
    box(ax,6.0,4.3,4.1,2.8,'ArduPilot SITL','NAV + DO görev motoru\nUçuş kontrol döngüsü')
    box(ax,11.3,4.3,4.0,2.8,'Gazebo','Araç fiziği\nDünya + RGB kamera')
    arrow(ax,(4.9,5.8),(5.9,5.8));arrow(ax,(10.2,6.1),(11.2,6.1));arrow(ax,(11.2,5.1),(10.2,5.1),GOLD)
    label(ax,10.75,6.65,'motor',14,ha='center');label(ax,10.75,4.65,'sensör',14,ha='center')
    box(ax,6.0,.8,9.3,2.3,'Python · görüntü işleme','RGB → mosaic / Gaussian Splatting / motion events')
    arrow(ax,(13.2,4.2),(13.2,3.2));arrow(ax,(8.05,4.2),(8.05,3.2),GOLD)
    label(ax,3.1,2.25,'Uçuş komutu\ngeri gönderilmez',23,TEAL,'bold',ha='center')
    save(fig,'ex_system','System and read-only vision data flow')

def camera():
    fig,ax=canvas()
    for i,H in enumerate([9,18,36]):
        x=2.7+i*5.25;w=H*2*math.tan(math.radians(35));top=6.8;ground=2.7;half=min(w/12,2.3)
        ax.add_patch(Polygon([(x,top),(x-half,ground),(x+half,ground)],color=TEAL,alpha=.12))
        ax.plot([x-half,x,x+half],[ground,top,ground],color=TEAL,lw=2);ax.add_patch(Circle((x,top),.14,color=NAVY))
        label(ax,x,7.55,f'{H} m',29,NAVY,'bold',ha='center');label(ax,x,2.1,f'{w:.1f} m footprint',21,ha='center');label(ax,x,1.25,f'{w/960*100:.1f} cm/px GSD',19,TEAL,'bold',ha='center')
    ax.plot([.5,15.5],[2.65,2.65],color=NAVY,lw=4);save(fig,'ex_camera_height','Same HFOV and resolution: altitude changes footprint and nominal GSD')

def footprint():
    fig,ax=canvas();x0,y0=.9,.9;w,h=8,6.35
    ax.add_patch(Rectangle((x0,y0),w,h,facecolor='#d8e9d7',edgecolor=NAVY,lw=2))
    for i in range(7):
        x=1.7+i*.96;ax.plot([x,x],[1.4,6.7],color=NAVY,lw=2,alpha=.65)
    for k,(x,y) in enumerate([(3.62,3.1),(3.62,4.1),(4.58,4.1)]):
        ax.add_patch(Rectangle((x-1.5,y-1.3),3,2.6,facecolor=[TEAL,GOLD,BLUE][k],edgecolor=[TEAL,GOLD,BLUE][k],alpha=.23,lw=3));ax.add_patch(Circle((x,y),.08,color=NAVY))
    arrow(ax,(3.62,3.1),(3.62,4.1),GOLD);arrow(ax,(3.62,4.1),(4.58,4.1),BLUE)
    box(ax,9.6,4.65,5.4,2.4,'Forward overlap','4 m trigger aralığı\n1 − 4 /16,8 ≈ %76')
    box(ax,9.6,1.45,5.4,2.4,'Side overlap','8 m flight-line aralığı\n1 − 8 /25,2 ≈ %68')
    save(fig,'ex_overlap','Image footprints and along/across-track overlap; concept, not to scale')

def spray():
    fig,ax=canvas();ax.add_patch(Rectangle((1.2,1.35),8.5,5.55,facecolor='#dcead7',edgecolor=NAVY,lw=2))
    for i in range(9):
        x=1.55+i*.97
        ax.plot([x,x],[1.1,7.1],color=TEAL,lw=31,alpha=.22,solid_capstyle='round');ax.plot([x,x],[1.1,7.1],color=NAVY,lw=1.6)
        if i<8:
            y=7.1 if i%2==0 else 1.1;ax.plot([x,x+.97],[y,y],color=GOLD,lw=3)
    box(ax,10.4,4.9,4.9,2,'ON · düz şerit','Pompa çıkışı yüksek',color=WHITE)
    box(ax,10.4,2.2,4.9,2,'OFF · dönüş','Pompa çıkışı düşük',color=WHITE)
    label(ax,5.5,.45,'9 flight line · 7 m spacing · 8 m ideal swath',20,NAVY,'bold',ha='center');save(fig,'ex_swath','AUTO pump-on/off geometry; ideal swath and headland extension')

def mission_timing():
    fig,ax=canvas()
    for i,(x,t) in enumerate([(1.5,'WP başlangıç'),(7.9,'WP bitiş'),(14.3,'Sonraki WP')]):
        ax.add_patch(Circle((x,5.6),.24,color=NAVY));label(ax,x,6.35,t,21,NAVY,'bold',ha='center')
    arrow(ax,(1.8,5.6),(7.55,5.6));arrow(ax,(8.2,5.6),(13.95,5.6),GOLD)
    ax.plot([1.5,1.5,7.9,7.9,14.3],[1.7,3.5,3.5,1.7,1.7],color=TEAL,lw=5)
    label(ax,4.5,4.0,'SPRAYER ON',23,TEAL,'bold',ha='center');label(ax,11.0,2.3,'SPRAYER OFF',23,GOLD,'bold',ha='center')
    arrow(ax,(1.5,5.3),(1.5,3.7),NAVY);arrow(ax,(7.9,5.3),(7.9,2),NAVY)
    label(ax,4.7,.65,'DO komutu, aktif NAV bacağı boyunca uygulanır.',23,ha='center')
    save(fig,'ex_nav_do','Waypoint and pump state timeline; correct NAV/DO ordering')

def mosaic():
    fig,ax=canvas();image(ax,'mapping_kamera.png',(0.5,4.9,3.6,7.9));image(ax,'mapping_kamera.png',(0.9,5.3,2.95,7.25));image(ax,'mapping_kamera.png',(1.35,5.75,2.3,6.6))
    arrow(ax,(6,4.6),(8.3,4.6));image(ax,'tarla_mozaik.png',(9.1,15.0,1.4,7.25))
    label(ax,3.1,1.3,'RGB + K + camera pose',23,NAVY,'bold',ha='center');label(ax,11.9,.65,'z = 0 planar mosaic',23,TEAL,'bold',ha='center')
    for a,b in [((3,2.6),(10,2)),((4,2.6),(13,2)),((3.5,3),(11.6,5))]:arrow(ax,a,b,TEAL,lw=1)
    save(fig,'ex_mosaic','Actual RGB frames projected to a common ground plane',['mapping_kamera.png','tarla_mozaik.png'])

def roi():
    fig,ax=canvas();cx,cy=7.8,4.15
    ax.add_patch(Ellipse((cx,cy),12,5.3,fill=False,edgecolor=TEAL,lw=3));ax.add_patch(Rectangle((cx-.8,cy-.8),1.6,1.6,facecolor=NAVY))
    label(ax,cx,cy,'ROI',24,WHITE,'bold',ha='center')
    for i,a in enumerate(np.linspace(0,2*math.pi,8,endpoint=False)):
        p=np.array([cx+6*math.cos(a),cy+2.65*math.sin(a)]);d=np.array([cx,cy])-p;d/=np.linalg.norm(d);r=np.array([-d[1],d[0]])
        ax.add_patch(Polygon([p,p+d*2+r*.75,p+d*2-r*.75],color=TEAL,alpha=.12));ax.add_patch(Circle(p,.13,color=GOLD));arrow(ax,p,np.array([cx,cy])-(np.array([cx,cy])-p)*.18,TEAL,lw=1.3)
    label(ax,8,.5,'AUTO trajectory + DO_SET_ROI + servo gimbal',24,NAVY,'bold',ha='center');save(fig,'ex_roi','Fixed ROI continuously drives the mount while AUTO flies the orbit')

def gaussian():
    fig=plt.figure(figsize=(16,6.6),facecolor=BG);ax=fig.add_axes([.01,.07,.56,.86],projection='3d');ax.set_facecolor(BG)
    u=np.linspace(0,2*np.pi,64);v=np.linspace(0,np.pi,32);x=2.2*np.outer(np.cos(u),np.sin(v));y=.85*np.outer(np.sin(u),np.sin(v));z=.55*np.outer(np.ones_like(u),np.cos(v))
    R=Rotation.from_euler('xyz',[20,25,-30],degrees=True).as_matrix();xyz=(R@np.array([x.ravel(),y.ravel(),z.ravel()])).reshape(3,*x.shape)
    ax.plot_surface(*xyz,color=TEAL,alpha=.45,linewidth=.3,edgecolor='#75b7ac');ax.scatter([0],[0],[0],color=GOLD,s=70)
    ax.set(xlim=(-2.5,2.5),ylim=(-2,2),zlim=(-1.5,1.5),xlabel='x',ylabel='y',zlabel='z');ax.view_init(23,-65);ax.set_box_aspect((1.5,1.2,1))
    a=fig.add_axes([.57,.06,.42,.9]);a.axis('off');a.set(xlim=(0,7),ylim=(0,8))
    for j,(t,b) in enumerate([('Position μ','Merkez: nerede?'),('Scale + rotation','Elipsoid: hangi yönde, ne kadar geniş?'),('Opacity α','Ne kadar görünür?'),('Color / SH','Bakış yönüne göre renk')]):box(a,.1,6.25-j*1.8,6.5,1.45,t,b)
    save(fig,'ex_gaussian','An anisotropic 3D Gaussian and its optimized parameter groups')

def projection():
    fig,ax=canvas()
    for k,(x,t) in enumerate([(2.6,'3D Gaussian'),(8.1,'2D splat'),(13.5,'Alpha blend')]):
        label(ax,x,7.35,t,25,NAVY,'bold',ha='center')
        if k==0:
            for i in range(6):ax.add_patch(Ellipse((x,4.4),4.3-i*.48,2.2-i*.24,angle=-28,facecolor=TEAL,edgecolor=TEAL,alpha=.08))
            label(ax,x,1.4,'K · camera pose',20,ha='center')
        elif k==1:
            for i in range(8):ax.add_patch(Ellipse((x,4.4),3.8-i*.35,2.7-i*.25,angle=25,facecolor=TEAL,alpha=.07))
            label(ax,x,1.4,'Ekrandaki footprint',20,ha='center')
        else:
            for xx,yy,c in [(x-.5,4.8,TEAL),(x+.45,4.2,GOLD),(x-.4,3.5,BLUE)]:ax.add_patch(Ellipse((xx,yy),2.25,1.6,angle=25,facecolor=c,alpha=.55))
            label(ax,x,1.4,'Depth order + opacity',20,ha='center')
    arrow(ax,(4.7,4.4),(5.9,4.4));arrow(ax,(10.2,4.4),(11.3,4.4));save(fig,'ex_splat_projection','Projection of anisotropic Gaussians and depth-aware alpha compositing')

def alpha():
    fig,ax=canvas()
    for j,order in enumerate([(TEAL,GOLD),(GOLD,TEAL)]):
        x=.8+j*7.65;box(ax,x,1.2,6.8,6,'Önce '+('teal' if j==0 else 'gold'))
        for c,(xx,yy) in zip(order,[(x+2.6,4.5),(x+3.6,3.6)]):ax.add_patch(Ellipse((xx,yy),3.9,2.6,angle=20,facecolor=c,alpha=.65))
        label(ax,x+3.4,1.9,'Aynı splat’ler, farklı görünüş',19,ha='center')
    label(ax,8,.45,'Compositing sırası derinliğe göre belirlenir.',24,NAVY,'bold',ha='center');save(fig,'ex_alpha','Ordering affects translucent splat appearance; conceptual alpha example')

def densify():
    fig,ax=canvas();rng=np.random.default_rng(2)
    for j,n in enumerate([8,24,100]):
        x=2.7+j*5.3
        for i in range(n):
            a=i*2.399963;r=math.sqrt((i+.5)/n)*1.8;px=x+math.cos(a)*r;py=4.5+math.sin(a)*r*.8
            ax.add_patch(Ellipse((px,py),1.6/math.sqrt(n/8),.7/math.sqrt(n/8),angle=40,facecolor=TEAL,alpha=.25))
        label(ax,x,7.1,['Initialization','Densification','Refinement'][j],24,NAVY,'bold',ha='center')
        label(ax,x,1.65,['Az sayıda büyük splat','İhtiyaç olan yerde büyüme','Daha ince renk ve yüzey'][j],19,ha='center')
    arrow(ax,(4.8,4.5),(5.6,4.5));arrow(ax,(10.1,4.5),(10.9,4.5));save(fig,'ex_densification','Concept of adaptive splat density; not claimed to be a measured checkpoint')

def holdout():
    fig,ax=canvas();cx,cy=7.8,4.3
    ax.add_patch(Rectangle((cx-.8,cy-.8),1.6,1.6,facecolor=NAVY));label(ax,cx,cy,'Bina',22,WHITE,'bold',ha='center')
    for i in range(32):
        a=2*math.pi*i/32;x=cx+6*math.cos(a);y=cy+2.8*math.sin(a);c=GOLD if i%8==0 else TEAL
        ax.add_patch(Circle((x,y),.13 if i%8 else .22,color=c))
        if i%8==0:arrow(ax,(x,y),(cx,cy),GOLD,lw=1.1)
    label(ax,4,.6,'Train · 94 görüntü',23,TEAL,'bold',ha='center');label(ax,12,.6,'Hold-out · 14 görüntü',23,GOLD,'bold',ha='center')
    save(fig,'ex_holdout','Train/eval view partition; hold-out images excluded from gradient optimization and sparse initialization')

def parallax():
    fig,ax=canvas();ax.plot([.8,15.2],[1.4,1.4],color=NAVY,lw=4)
    for x,c in [(3,TEAL),(12,GOLD)]:
        ax.add_patch(Circle((x,6.8),.2,color=c));label(ax,x,7.6,'Camera '+('A' if x==3 else 'B'),23,c,'bold',ha='center')
        arrow(ax,(x,6.5),(7.5,1.5),c,lw=2);arrow(ax,(x,6.5),(10.3,4.5),c,lw=2)
    ax.plot([10.3,10.3],[1.4,4.6],color='#79624d',lw=12);ax.add_patch(Polygon([[8.9,3.2],[10.3,5.2],[11.7,3.2]],color='#58874b'))
    label(ax,4,2.0,'Zemin düzlemi',21,ha='center');label(ax,12.9,3.8,'Ağaç farklı\nderinlikte',22,ha='center')
    label(ax,8,.55,'Tek homography, bütün derinlikleri hizalayamaz.',24,NAVY,'bold',ha='center');save(fig,'ex_parallax','Depth-dependent motion creates parallax and potential false alarms')

def motion_flow():
    fig,ax=canvas();image(ax,'hareket_ham.png',(.5,5.2,3.1,7.8));image(ax,'hareket_artik.png',(5.65,10.35,3.1,7.8));image(ax,'hareket.png',(10.8,15.5,3.1,7.8))
    for x,t,b in [(2.8,'RGB','Camera motion + target motion'),(8,'Residual mask','Homography ile background telafisi'),(13.15,'Motion candidate','Temporal confirmation + crop')]:label(ax,x,2.25,t,24,NAVY,'bold',ha='center');label(ax,x,1.35,b,17,ha='center')
    arrow(ax,(5.15,5.4),(5.65,5.4));arrow(ax,(10.3,5.4),(10.8,5.4));save(fig,'ex_motion_stages','Real input, compensated residual, and live event output',['hareket_ham.png','hareket_artik.png','hareket.png'])

def homography():
    import cv2
    run=ROOT/'simulasyon/.local/runs/20261027-190335-plane'
    if not run.exists():return
    prev=cv2.imread(str(run/'camera/000106.png'));cur=cv2.imread(str(run/'camera/000108.png'))
    orb=cv2.ORB_create(nfeatures=4000,fastThreshold=3);ka,da=orb.detectAndCompute(prev,None);kb,db=orb.detectAndCompute(cur,None)
    raw=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2);matches=[a for pair in raw if len(pair)==2 for a,b in [pair] if a.distance<.74*b.distance]
    pa=np.float32([ka[m.queryIdx].pt for m in matches]);pb=np.float32([kb[m.trainIdx].pt for m in matches]);H,mask=cv2.findHomography(pa,pb,cv2.RANSAC,2.5)
    good=[m for m,k in zip(matches,mask.ravel()) if k];draw=cv2.drawMatches(prev,ka,cur,kb,good[::max(1,len(good)//35)],None,matchColor=(110,210,70),flags=2)
    aligned=cv2.warpPerspective(prev,H,(cur.shape[1],cur.shape[0]));diff=cv2.absdiff(aligned,cur)
    name='homography_matches.png';Image.fromarray(cv2.cvtColor(draw,cv2.COLOR_BGR2RGB)).save(A/name)
    Image.fromarray(cv2.cvtColor(aligned,cv2.COLOR_BGR2RGB)).save(A/'homography_aligned.png')
    fig,ax=canvas();ax.imshow(cv2.cvtColor(draw,cv2.COLOR_BGR2RGB),extent=(.5,10.6,2.3,7.3));ax.imshow(cv2.cvtColor(aligned,cv2.COLOR_BGR2RGB),extent=(11,15.5,3.1,6.3))
    label(ax,5.5,7.8,'Feature matching + RANSAC',24,NAVY,'bold',ha='center');label(ax,13.2,7.1,'Warped frame',23,NAVY,'bold',ha='center')
    label(ax,5.5,1.4,f'{len(matches)} matches → {len(good)} inliers',23,TEAL,'bold',ha='center');label(ax,13.2,2.2,"x′ ~ H x",26,TEAL,'bold',ha='center')
    save(fig,'ex_homography','Actual ORB matches, RANSAC inliers and previous-to-current camera-frame warp',['.local/runs/20261027-190335-plane/camera/000106.png','.local/runs/20261027-190335-plane/camera/000108.png'])

def timeline():
    fig,ax=canvas();ax.plot([1,15],[4.7,4.7],color=NAVY,lw=4)
    for x,t,b,c in [(1.4,'Takeoff','Görev başladı',NAVY),(4.1,'Live event','AUTO10 · NAV3',GOLD),(9.2,'Fixed scan','Rota değişmedi',TEAL),(14.4,'LAND','Disarm',NAVY)]:
        ax.add_patch(Circle((x,4.7),.18,color=c));label(ax,x,5.75,t,21,c,'bold',ha='center');label(ax,x,3.75,b,18,ha='center')
    arrow(ax,(4.1,2.25),(14.4,2.25),GOLD);label(ax,9.25,1.45,'İlk canlı olaydan sonra ~317 s AUTO devam',25,NAVY,'bold',ha='center');save(fig,'ex_event_timeline','Measured live event-to-landing timing from final Plane telemetry')

def model_figures():
    if not (A/'gaussian_final.png').exists():return
    fig,ax=canvas();image(ax,'gaussian_reference.png',(.5,5.1,2,6.6));image(ax,'gaussian_final.png',(5.7,10.3,2,6.6));image(ax,'gaussian_difference.png',(10.9,15.5,2,6.6))
    for x,t in [(2.8,'Reference RGB'),(8,'Rendered RGB'),(13.2,'Difference ×4')]:label(ax,x,7.25,t,24,NAVY,'bold',ha='center')
    label(ax,8,.9,'Render → loss → gradient → parameter update',27,TEAL,'bold',ha='center');save(fig,'ex_training_loop','Actual held-out reference/render/error; optimized model never reads the source mesh',['gaussian_reference.png','gaussian_final.png','gaussian_difference.png'])
    fig,ax=canvas()
    for i,name in enumerate(['gaussian_step1000.png','gaussian_step3000.png','gaussian_final.png']):
        if not (A/name).exists():continue
        image(ax,name,(.4+i*5.25,5.1+i*5.25,2,6.7));label(ax,2.75+i*5.25,7.3,['1 000 steps','3 000 steps','6 000 steps'][i],25,NAVY,'bold',ha='center')
    label(ax,8,.9,'Aynı hold-out view · aynı training run',24,TEAL,'bold',ha='center');save(fig,'ex_training_progress','Actual checkpoint renders from the same final optimization run')

def main():
    for fn in [system,camera,footprint,spray,mission_timing,mosaic,roi,gaussian,projection,alpha,densify,holdout,parallax,homography,motion_flow,timeline,model_figures]:fn()
    (A/'explainers-provenance.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'explanatory_figures':len(manifest),'editable_svg_sources':str(V)}))
if __name__=='__main__':main()
