"""Instructor integration test for two local GCS links and the camera intro.

The simulated operator sends upload/start commands on5760; the student recorder
only observes on5762. Every process belongs to this local Session.
"""
from __future__ import annotations
import copy,json,subprocess,time
from runtime import Session,ROOT
from fly_auto import GCS,MISSIONS

def main():
    s=Session('intro',gui=True);observer=GCS(s,5762);operator=None
    try:
        s.start();observer.connect();observer.ready()
        mission=json.loads((ROOT/'missions'/f'{MISSIONS["intro"]}.json').read_text());(s.run/'mission.json').write_text(json.dumps(mission,indent=2))
        op=copy.copy(s);op.run=s.run/'operator';op.run.mkdir();operator=GCS(op,5760);operator.connect();operator.ready()
        # Move only the GUI observer camera. This is not a vehicle setpoint.
        gz=[str(s.config['pixi']),'run','--manifest-path',str(s.config['manifest']),'gz']
        queries=[]
        for service in ('/gui/move_to',):
            p=subprocess.run(gz+['service','-is',service],env=s.env,capture_output=True,text=True,timeout=15);queries.append({'service':service,'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode})
        (s.run/'gui-services.json').write_text(json.dumps(queries,indent=2))
        p=subprocess.run(gz+['service','-s','/gui/move_to','--reqtype','gz.msgs.StringMsg','--reptype','gz.msgs.Boolean','--timeout','5000','--req','data: "iris_with_ardupilot"'],env=s.env,capture_output=True,text=True,timeout=15)
        time.sleep(2)
        (s.run/'gui-check.json').write_text(json.dumps({'move_output':p.stdout,'move_error':p.stderr,'gui_view_navigation_accepted':'data: true' in p.stdout},indent=2))
        operator.upload(mission);operator.start_auto(False);operator.status='operator_uploaded_and_started_auto'
        observer.observe(False,len(mission['items'])-1,300);observer.status='auto_mission_passed';observer.harvest();observer.save()
        print(json.dumps({'run':str(s.run),'observer_command_longs':observer.sent,'operator_command_longs':operator.sent,'gui_navigation':'data: true' in p.stdout}),flush=True)
        if observer.sent:raise RuntimeError('Passive observer sent a flight command')
    except BaseException as e:
        observer.status='failed';observer.event('integration_failure',error=str(e));raise
    finally:
        observer.close()
        if operator:operator.close()
        s.close()
if __name__=='__main__':main()
