"""Shared, dependency-free driving input and third-person presentation, in metres and radians."""
import bisect
import math

def clamp(value, low, high):
    return max(low, min(high, value))

def approach(value, target, step):
    return value + clamp(target - value, -step, step)

def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi

class Driver:
    defaults = dict(forward=6.4, reverse=3.2, gauge=3.3, yaw_rate=1.5, pitch_rate=.82,
                    hatch_rate=.82, hatch_limit=1.18)

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

    def snapshot(self):
        return {**vars(self), 'parameters':dict(self.parameters), 'travel':list(self.travel)}

    @classmethod
    def restore(cls, state):
        driver = cls(state['parameters'])
        for key in vars(driver).copy():
            if key not in ('travel','parameters'):
                setattr(driver,key,state[key])
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

    def step(self, dt, throttle=0, steer=0, brake=False, physics_heading=None):
        dt=clamp(dt, 0, .05)
        cfg=self.parameters
        v = throttle * (cfg['forward'] if throttle >= 0 else cfg['reverse'])
        steer = steer * (1.65 + .22 * abs(v))
        target = (v-steer, v+steer)
        for key,goal in zip(('left','right'),target):
            old = getattr(self,key)
            rate = 10.5 if brake else (3.2 if goal or old*goal < 0 else 2.1)
            setattr(self,key,approach(old,0.0 if brake else goal,rate*dt))
        if physics_heading is None:
            speed = .5 * (self.left+self.right)
            omega = (self.right-self.left)/cfg['gauge']
            mid = self.heading + .5*dt*omega
            self.x += dt*speed*math.cos(mid)
            self.y += dt*speed*math.sin(mid)
            self.heading = wrap(self.heading+dt*omega)
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

