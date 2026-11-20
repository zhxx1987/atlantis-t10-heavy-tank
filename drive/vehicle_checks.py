"""Deterministic regression, run unchanged in CPython and browser Pyodide."""
def check_vehicle_dynamics():
    h=1/120
    def run(d,n,throttle=0,steer=0,brake=False,terrain=None):
        trace=[]
        for _ in range(round(n/h)):
            d.advance(h,throttle,steer,brake,terrain)
            trace.append(d.snapshot())
        return trace
    d=Driver();run(d,3,1);start=d.x;stop=run(d,4,brake=True)
    dip=min(s['pitch'] for s in stop)
    assert -.105<dip<-.0087 and abs(d.pitch)<.0001 and d.speed==0
    brake_distance=d.x-start;held=d.x;run(d,2,brake=True);assert d.x==held
    c=Driver();run(c,3,1);start=c.x;run(c,4);coast_distance=c.x-start
    assert brake_distance<coast_distance*.4
    r=Driver();run(r,3,1);trace=run(r,2,-1)
    first=next(i for i,s in enumerate(trace) if s['speed']<0)
    assert any(s['speed']==0 for s in trace[:first])
    a=Driver();a.z=2;a.grounded=0;a.contacts=[False]*14;flight=run(a,5,1)
    assert flight[20]['grounded']==0 and abs(flight[20]['x'])<1e-10
    assert abs(a.z+.0025)<.002 and abs(a.vz)<.005
    profile={'floor':-.03,'lane_half_width':8,'patches':[[13,16,.12,4.8],[20,24,.18,4.8],[31,47,.7,4.8]]}
    b=Driver();bumps=run(b,12,1,terrain=profile)
    assert max(s['z'] for s in bumps)>.45
    assert max(max(s['suspension'])-min(s['suspension']) for s in bumps)>.12
    side=Driver();side.y=4.5;side_trace=run(side,6,1,terrain=profile)
    assert max(abs(s['roll']) for s in side_trace)>.01
    flat=Driver();flat_trace=run(flat,12,1)
    assert max(abs(s['pitch']) for s in flat_trace[-360:])<1e-5
    results=[]
    for fps in (30,60,144):
        t=Driver()
        for _ in range(6*fps):t.advance(1/fps,1)
        results.append(t.x)
    assert max(results)-min(results)<1e-8
    assert Driver.restore(b.snapshot()).snapshot()==b.snapshot()
    native=Driver();native.step(h,1,physics_heading=.7)
    assert native.x==native.y==native.z==0 and native.heading==.7
    return {'checks':dict(braking_and_hold=True,brake_dip_settle=True,coasting=True,stop_before_reverse=True,airborne_landing=True,bumps=True,one_side_bump_roll=True,flat_no_jitter=True,fixed_step_30_60_144=True,snapshot=True,native_no_double_integration=True),'brake_distance_m':brake_distance,'coast_distance_m':coast_distance,'brake_dip_degrees':math.degrees(dip)}
