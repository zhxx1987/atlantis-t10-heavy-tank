"""Shared, dependency-free driving input and third-person presentation, in metres and radians."""
import bisect
import math
import copy

def ground_height(x, y, terrain=None):
    """Collision surface shared with the course mesh (metres, Z up)."""
    terrain = terrain or {}
    h = terrain.get('floor', -.03)
    if abs(y) <= terrain.get('lane_half_width', 8) and -145 <= x <= 185:
        h = max(h, -.0025)
    for a,b,height,width in terrain.get('patches', []):
        if a < x < b and abs(y) < width:
            edge = clamp((width-abs(y))/.6, 0, 1)
            h = max(h, -.0025 + height*math.sin(math.pi*(x-a)/(b-a))**2*edge)
    return h

def clamp(value, low, high):
    return max(low, min(high, value))

def approach(value, target, step):
    return value + clamp(target - value, -step, step)

def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi

class Driver:
    defaults = dict(forward=6.4, reverse=3.2, gauge=3.3, yaw_rate=1.5, pitch_rate=.82,
                    hatch_rate=.82, hatch_limit=1.18, acceleration=3.2, coast=2.1,
                    braking=10.5, wheelbase=5.16, suspension_travel=.22, suspension_droop=.05,
                    spring=36.0, damping=8.6, ride_clearance=0.0)

    def __init__(self, parameters=None):
        self.parameters = {**self.defaults, **(parameters or {})}
        self.left = self.right = self.x = self.y = self.heading = 0.0
        self.travel = [0.0, 0.0]
        self.look = self.tilt = self.turret = self.elevation = 0.0
        self.effect = 1.0
        self.shots = 0
        self.recoil = self.flash = 0.0
        self.hatches_open = False
        self.hatch = 0.0
        self.speed = self.omega = self.acceleration = 0.0
        self.z = self.vz = self.pitch = self.roll = 0.0
        self.pitch_velocity = self.roll_velocity = 0.0
        self.contacts = [True]*14
        self.suspension = [0.0]*14
        self.grounded = 14
        self.braking = self.reverse_braking = False
        self.accumulator = 0.0

    def snapshot(self):
        return copy.deepcopy(vars(self))

    @classmethod
    def restore(cls, state):
        driver = cls(state['parameters'])
        for key in vars(driver).copy():
            if key not in ('travel','parameters'):
                setattr(driver,key,copy.deepcopy(state.get(key,getattr(driver,key))))
        driver.travel=list(state['travel'])
        return driver

    def mouse(self, dx, dy):
        self.look = wrap(self.look - dx * .0032)
        self.tilt = clamp(self.tilt - dy * .0024, -.18, .43)

    def fire(self):
        if self.effect < .55:
            return False
        self.effect = 0.0
        self.shots += 1
        return True

    def step(self, dt, throttle=0, steer=0, brake=False, physics_heading=None, terrain=None):
        dt=clamp(dt, 0, .05)
        cfg=self.parameters
        if dt <= 0: return
        throttle=clamp(throttle,-1,1);steer=clamp(steer,-1,1)
        speed = self.speed if physics_heading is None else .5*(self.left+self.right)
        # Keep reverse input in the braking state until both belts and the
        # chassis actually reach zero. Do not cross zero within that step.
        opposed = throttle*speed < -1e-10
        stopping = self.reverse_braking and any(abs(v)>1e-10 for v in (speed,self.left,self.right))
        self.reverse_braking = bool(throttle and (opposed or stopping))
        self.braking = bool(brake or self.reverse_braking)
        v = throttle * (cfg['forward'] if throttle >= 0 else cfg['reverse'])
        steer = steer * (1.65 + .22 * abs(v))
        target = (v-steer, v+steer)
        for key,goal in zip(('left','right'),target):
            old = getattr(self,key)
            rate = cfg['braking'] if self.braking else (cfg['acceleration'] if goal else cfg['coast'])
            setattr(self,key,approach(old,0.0 if self.braking else goal,rate*dt))
        if physics_heading is None:
            traction = self.grounded/len(self.contacts)
            old_speed=self.speed
            rate=cfg['braking'] if self.braking else cfg['acceleration'] if throttle else cfg['coast']
            self.speed=approach(self.speed,.5*(self.left+self.right),rate*traction*dt)
            self.omega=approach(self.omega,(self.right-self.left)/cfg['gauge'],3*traction*dt)
            self.acceleration=(self.speed-old_speed)/dt
            speed,omega=self.speed,self.omega
            mid = self.heading + .5*dt*omega
            self.x += dt*speed*math.cos(mid)
            self.y += dt*speed*math.sin(mid)
            self.heading = wrap(self.heading+dt*omega)
            self.ride_step(dt, terrain)
        else:
            self.heading = physics_heading
        for i,speed in enumerate((self.left,self.right)):
            self.travel[i] += dt*speed
        self.turret = wrap(self.turret + clamp(wrap(self.look-self.heading-self.turret),-cfg['yaw_rate']*dt,cfg['yaw_rate']*dt))
        self.elevation = approach(self.elevation,self.tilt,cfg['pitch_rate']*dt)
        self.hatch = approach(self.hatch,cfg['hatch_limit'] if self.hatches_open else 0,cfg['hatch_rate']*dt)
        self.effect += dt
        t=self.effect
        self.flash = max(0., 1.-t/.105)
        self.recoil = .17 * min(t/.045,1.) * max(0.,1.-max(0.,t-.045)/.26)**2

    def ride_step(self, dt, terrain=None):
        """Bounded spring contacts and three chassis DOFs; no rigid track chain.

        Nominal spring compression balances gravity. Contact is unilateral;
        an airborne body falls and keeps its horizontal momentum.
        """
        cfg=self.parameters;travel=cfg['suspension_travel'];k=cfg['spring'];d=cfg['damping']
        c,s=math.cos(self.heading),math.sin(self.heading)
        xs=[-2.61+i*cfg['wheelbase']/6 for i in range(7)]
        anchors=[(x,side*cfg['gauge']/2) for side in (1,-1) for x in xs]
        force=pitch_force=roll_force=0.0
        cx=sum(xs)/len(xs)
        xx=sum((x-cx)**2 for x,y in anchors)/14; yy=sum(y*y for x,y in anchors)/14
        for i,(x,y) in enumerate(anchors):
            h=ground_height(self.x+c*x-s*y,self.y+s*x+c*y,terrain)+cfg['ride_clearance']
            body_h=self.z+x*math.sin(self.pitch)+y*math.sin(self.roll)
            delta=h-body_h
            touching=delta >= -cfg['suspension_droop']
            self.contacts[i]=touching
            self.suspension[i]=clamp(delta,-cfg['suspension_droop'],travel)
            velocity=self.vz+x*self.pitch_velocity+y*self.roll_velocity
            load=clamp(9.81+k*delta-d*velocity,0,65) if touching else 0
            load+=min(120,max(0,delta-travel)*350)
            force+=load/14;pitch_force+=(x-cx)*load/(14*xx);roll_force+=y*load/(14*yy)
        self.grounded=sum(self.contacts)
        self.vz+=(force-9.81)*dt
        self.z+=self.vz*dt
        transfer=clamp(self.acceleration*.009,-.075,.035)*(self.grounded/14)
        self.pitch_velocity+=(pitch_force+k*transfer)*dt
        self.roll_velocity+=(roll_force-clamp(self.speed*self.omega*.012,-.07,.07)*k*self.grounded/14)*dt
        self.pitch=clamp(self.pitch+self.pitch_velocity*dt,-.32,.32)
        self.roll=clamp(self.roll+self.roll_velocity*dt,-.25,.25)

    def advance(self, dt, throttle=0, steer=0, brake=False, terrain=None):
        """Persistent fixed-step accumulator; discard a long tab suspension."""
        self.accumulator+=clamp(dt,0,.1)
        h=1/120
        while self.accumulator+1e-12>=h:
            self.step(h,throttle,steer,brake,terrain=terrain)
            self.accumulator-=h

    def camera(self, xyz):
        x,y,z=xyz
        pitch=.24 + .35*self.tilt
        c=math.cos(pitch)
        pivot=(x+.45*math.cos(self.look),y+.45*math.sin(self.look),z+1.65)
        return ([pivot[0]-9.6*c*math.cos(self.look),pivot[1]-9.6*c*math.sin(self.look),pivot[2]+9.6*math.sin(pitch)],list(pivot))

def track_pin(rig, distance, suspension=None):
    contour,cum=rig['contour'],rig['distance']
    distance %= cum[-1]
    i=min(bisect.bisect_right(cum,distance)-1,len(cum)-2)
    f=(distance-cum[i])/(cum[i+1]-cum[i])
    a,b=contour[i:i+2]
    x = a[0]+(b[0]-a[0])*f
    z = a[1]+(b[1]-a[1])*f
    if suspension is not None and z < .42:
        wheels = rig['road']
        j = max(0, min(len(wheels)-2, bisect.bisect_right(wheels,x)-1))
        blend = clamp((x-wheels[j])/(wheels[j+1]-wheels[j]),0,1)
        delta = suspension[j]+blend*(suspension[j+1]-suspension[j])
        z += delta*clamp((.42-z)/.36,0,1)
    return x,z

def link_pose(rig, distance, suspension=None):
    half_pitch = .5*rig['distance'][-1]/rig['count']
    ax,az = track_pin(rig,distance-half_pitch,suspension)
    bx,bz = track_pin(rig,distance+half_pitch,suspension)
    return (ax+bx)/2,(az+bz)/2,-math.atan2(bz-az,bx-ax)

