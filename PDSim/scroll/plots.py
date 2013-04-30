
fig_size =  [8,10]

import glob
import math
from math import atan2
import numpy as np
import pylab
from pylab import arange,pi,sin,cos,sqrt,tan
import threading
import wx

import os,subprocess
#import scrollCalcs as Calcs
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
global geo,setDiscGeo,coords_inv,circle,sortAnglesCCW,Shave,plotScrollSet
global polyarea,theta_d
import scipy.optimize as optimize
import matplotlib.pyplot as pyplot
    
class geoVals:
    """ 
    A class which contains the fields related the 
    scroll compressor geometry
    """
    # Default values for Sanden Compressor #
    ## DO NOT MODIFY THESE VALUES ##
    rb=0.003522
    phi_i0=0.19829
    phi_is=4.7
    phi_ie=15.5
    phi_o0=-1.1248
    phi_os=1.8
    phi_oe=15.5
    h=0.03289
    disc_x0=-0.007	
    disc_y0=-0.0011	
    disc_R=0.0060198

    def __init__(self, **kwargs):
        self.Load()
    def Load(self):
        # Default values for Sanden Compressor #
        ## DO NOT MODIFY THESE VALUES ##
        self.rb=0.003522
        self.phi_i0=0.19829
        self.phi_is=4.7
        self.phi_ie=15.5
        self.phi_o0=-1.1248
        self.phi_os=1.8
        self.phi_oe=15.5
        self.h=0.03289
        disc_x0=-0.007	
        disc_y0=-0.0011	
        disc_R=0.0060198
        self.ro=self.rb*(pi-self.phi_i0+self.phi_o0)
        #Load a default discharge geometry
        setDiscGeo(self)

def LoadGeo():
    """
    Returns a class containing the default parameters for the scroll compressor
    
    =======   =========
    r_b       0.003522 
    phi_i0    0.19829
    phi_is    4.7
    phi_ie    15.5
    phi_o0    -1.1248
    phi_os    1.8
    phi_oe    15.5
    h         0.03289
    disc_x0   -0.007
    disc_y0   -0.0011
    disc_R    0.0060198
    =======   =========
    
    """
    return geoVals()
    
def setDiscGeo(geo,Type='Sanden',r2=0.001,**kwargs):
    """
    Sets the discharge geometry for the compressor based on the arguments.
    Also sets the radius of the wall that contains the scroll set
    
    Arguments:
        geo : geoVals class
            class containing the scroll compressor geometry
        Type : string
            Type of discharge geometry, options are ['Sanden'],'2Arc','ArcLineArc'
        r2 : float or string
            Either the radius of the smaller arc as a float or 'PMP' for perfect meshing
            If Type is 'Sanden', this value is ignored
    
    Keyword Arguments:
    
    ========     ======================================================================
    Value        Description
    ========     ======================================================================
    r1           the radius of the large arc for the arc-line-arc solution type
    ========     ======================================================================
    
    """
    
    #Recalculate the orbiting radius
    geo.ro=geo.rb*(pi-geo.phi_i0+geo.phi_o0)
    if Type == 'Sanden':
        geo.x0_wall=0.0
        geo.y0_wall=0.0
        geo.r_wall=0.065
        setDiscGeo(geo,Type='ArcLineArc',r2=0.003178893902,r1=0.008796248080)
    elif Type == '2Arc':
        (x_is,y_is) = coords_inv(geo.phi_is,geo,0,'fi')
        (x_os,y_os) = coords_inv(geo.phi_os,geo,0,'fo')
        (nx_is,ny_is) = coords_norm(geo.phi_is,geo,0,'fi')
        (nx_os,ny_os) = coords_norm(geo.phi_os,geo,0,'fo')
        dx=x_is-x_os
        dy=y_is-y_os
        
        r2max=0
        a=cos(geo.phi_os-geo.phi_is)+1.0
        b=geo.ro*a-dx*(sin(geo.phi_os)-sin(geo.phi_is))+dy*(cos(geo.phi_os)-cos(geo.phi_is))
        c=1.0/2.0*(2.0*dx*sin(geo.phi_is)*geo.ro-2.0*dy*cos(geo.phi_is)*geo.ro-dy**2-dx**2)
        if geo.phi_os-(geo.phi_is-pi)>1e-12:
            r2max=(-b+sqrt(b**2-4.0*a*c))/(2.0*a)
        elif geo.phi_os==geo.phi_is-pi:
            r2max=-c/b
        else:
            print 'error with starting angles phi_os %.16f phi_is-pi %.16f' %(geo.phi_os,geo.phi_is-pi)
            
        if type(r2) is not float and r2=='PMP':
            r2=r2max
            
        if r2>r2max:
            print 'r2 is too large, max value is : %0.5f' %(r2max)
        
        xarc2 =  x_os+nx_os*r2
        yarc2 =  y_os+ny_os*r2
        
        r1=((1.0/2*dy**2+1.0/2*dx**2+r2*dx*sin(geo.phi_os)-r2*dy*cos(geo.phi_os))
               /(r2*cos(geo.phi_os-geo.phi_is)+dx*sin(geo.phi_is)-dy*cos(geo.phi_is)+r2))
        
        
        ## Negative sign since you want the outward pointing unit normal vector
        xarc1 =  x_is-nx_is*r1
        yarc1 =  y_is-ny_is*r1
                
        geo.xa_arc2=xarc2
        geo.ya_arc2=yarc2
        geo.ra_arc2=r2
        geo.t1_arc2=math.atan2(yarc1-yarc2,xarc1-xarc2)
        geo.t2_arc2=math.atan2(y_os-yarc2,x_os-xarc2)
        while geo.t2_arc2<geo.t1_arc2:
            geo.t2_arc2=geo.t2_arc2+2.0*pi;
    
        geo.xa_arc1=xarc1
        geo.ya_arc1=yarc1
        geo.ra_arc1=r1
        geo.t2_arc1=math.atan2(y_is-yarc1,x_is-xarc1)
        geo.t1_arc1=math.atan2(yarc2-yarc1,xarc2-xarc1)
        while geo.t2_arc1<geo.t1_arc1:
            geo.t2_arc1=geo.t2_arc1+2.0*pi;
        
        """ 
        line given by y=m*t+b with one element at the intersection
        point
        
        with b=0, m=y/t
        """
        geo.b_line=0.0
        geo.t1_line=xarc2+r2*cos(geo.t1_arc2)
        geo.t2_line=geo.t1_line
        geo.m_line=(yarc2+r2*sin(geo.t1_arc2))/geo.t1_line
        
        """ 
        Fit the wall to the chamber
        """
        geo.x0_wall=geo.ro/2.0*cos(geo.phi_ie-pi/2-pi)
        geo.y0_wall=geo.ro/2.0*sin(geo.phi_ie-pi/2-pi)
        (x,y)=coords_inv(geo.phi_ie,geo,pi,'fo')
        geo.r_wall=1.03*sqrt((geo.x0_wall-x)**2+(geo.y0_wall-y)**2)
    elif Type=='ArcLineArc':
        (x_is,y_is) = coords_inv(geo.phi_is,geo,0,'fi')
        (x_os,y_os) = coords_inv(geo.phi_os,geo,0,'fo')
        (nx_is,ny_is) = coords_norm(geo.phi_is,geo,0,'fi')
        (nx_os,ny_os) = coords_norm(geo.phi_os,geo,0,'fo')
        dx=x_is-x_os
        dy=y_is-y_os
        
        r2max=0
        a=cos(geo.phi_os-geo.phi_is)+1.0
        b=geo.ro*a-dx*(sin(geo.phi_os)-sin(geo.phi_is))+dy*(cos(geo.phi_os)-cos(geo.phi_is))
        c=1.0/2.0*(2.0*dx*sin(geo.phi_is)*geo.ro-2.0*dy*cos(geo.phi_is)*geo.ro-dy**2-dx**2)
        if geo.phi_os-(geo.phi_is-pi)>1e-12:
            r2max=(-b+sqrt(b**2-4.0*a*c))/(2.0*a)
        elif geo.phi_os-(geo.phi_is-pi)<1e-12:
            r2max=-c/b
        else:
            print 'error with starting angles phi_os %.16f phi_is-pi %.16f' %(geo.phi_os,geo.phi_is-pi)
            
        if type(r2) is not float and r2=='PMP':
            r2=r2max
                
        if r2>r2max:
            print 'r2 is too large, max value is : %0.5f' %(r2max)
        
        xarc2 =  x_os+nx_os*r2
        yarc2 =  y_os+ny_os*r2
        
        if 'r1' not in kwargs:
            r1=r2+geo.ro
        else:
            r1=kwargs['r1']
        
        ## Negative sign since you want the outward pointing unit normal vector
        xarc1 =  x_is-nx_is*r1
        yarc1 =  y_is-ny_is*r1
                
        geo.xa_arc2=xarc2
        geo.ya_arc2=yarc2
        geo.ra_arc2=r2
        geo.t2_arc2=math.atan2(y_os-yarc2,x_os-xarc2)
    
        geo.xa_arc1=xarc1
        geo.ya_arc1=yarc1
        geo.ra_arc1=r1
        geo.t2_arc1=math.atan2(y_is-yarc1,x_is-xarc1)
                
        alpha=math.atan2(yarc2-yarc1,xarc2-xarc1)
        d=sqrt((yarc2-yarc1)**2+(xarc2-xarc1)**2)
        beta=math.acos((r1+r2)/d)
        L=sqrt(d**2-(r1+r2)**2)
        t1=alpha+beta
        
        (xint,yint)=(xarc1+r1*cos(t1)+L*sin(t1),yarc1+r1*sin(t1)-L*cos(t1))
        t2=math.atan2(yint-yarc2,xint-xarc2)
        
        geo.t1_arc1=t1
#        (geo.t1_arc1,geo.t2_arc1)=sortAnglesCW(geo.t1_arc1,geo.t2_arc1)
        
        geo.t1_arc2=t2
#        (geo.t1_arc2,geo.t2_arc2)=sortAnglesCCW(geo.t1_arc2,geo.t2_arc2)

        while geo.t2_arc2<geo.t1_arc2:
            geo.t2_arc2=geo.t2_arc2+2.0*pi;
        while geo.t2_arc1<geo.t1_arc1:
            geo.t2_arc1=geo.t2_arc1+2.0*pi;
        """ 
        line given by y=m*t+b with one element at the intersection
        point
        
        with b=0, m=y/t
        """
        geo.m_line=-1/tan(t1)
        geo.t1_line=xarc1+r1*cos(geo.t1_arc1)
        geo.t2_line=xarc2+r2*cos(geo.t1_arc2)
        geo.b_line=yarc1+r1*sin(t1)-geo.m_line*geo.t1_line
        
        """ 
        Fit the wall to the chamber
        """
        geo.x0_wall=geo.ro/2.0*cos(geo.phi_ie-pi/2-pi)
        geo.y0_wall=geo.ro/2.0*sin(geo.phi_ie-pi/2-pi)
        (x,y)=coords_inv(geo.phi_ie,geo,pi,'fo')
        geo.r_wall=1.03*sqrt((geo.x0_wall-x)**2+(geo.y0_wall-y)**2)
        
#        f=pylab.Figure
#        pylab.plot(x_os,y_os,'o')
#        x=geo.xa_arc1+geo.ra_arc1*cos(np.linspace(geo.t1_arc1,geo.t2_arc1,100))
#        y=geo.ya_arc1+geo.ra_arc1*sin(np.linspace(geo.t1_arc1,geo.t2_arc1,100))
#        pylab.plot(x,y)
#        x=geo.xa_arc2+geo.ra_arc2*cos(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
#        y=geo.ya_arc2+geo.ra_arc2*sin(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
#        pylab.plot(x,y)
#        x=np.linspace(geo.t1_line,geo.t2_line,100)
#        y=geo.m_line*x+geo.b_line
#        pylab.plot(x,y)
#        pylab.plot(xint,yint,'^')
#        pylab.show()
    else:
        print 'Type not understood:',Type
        
         
    
def phi_ssa(theta,**kwargs):
    """
    Returns the break angle on the outer involute of
    the orbiting scroll which defines the line between the 
    :math:: 'sa' and s1 chambers scroll wrap c

    Arguments:
        theta : float
            The crank angle in radians

    Optional Parameters
    
    ======  =======================================
    key     value
    ======  =======================================
    geo     The class that defines the geometry of the compressor.
    ======  =======================================

    """
    if 'geo' in kwargs:
        geo=kwargs['geo']
    else:
        geo=LoadGeo()
    #residual function to be minimized to get the intersection line
    def f(phi_ssa):
        (xe,ye)=coords_inv(geo.phi_ie, geo, theta, 'fi')
        (xssa,yssa)=coords_inv(phi_ssa, geo, theta, 'oo')
        return xssa*ye-yssa*xe
    phissa=optimize.fsolve(f, geo.phi_ie-pi)
    return phissa

def Nc(theta,**kwargs):
    """ 
    The number of pairs of compression chambers in existence at a given 
    crank angle 
    
    Arguments:
        theta : float
            The crank angle in radians.

    Returns:
        Nc : int
            Number of pairs of compressions chambers

    Optional Parameters
    
    ======  =======================================
    key     value
    ======  =======================================
    geo     The class that defines the geometry of the compressor.
    ======  =======================================
        
    """
    
    geo=kwargs.get('geo',LoadGeo())
    return int(np.floor((geo.phi_ie-theta-geo.phi_os-pi)/(2*pi)))
    
def theta_d(**kwargs):  
    """ 
    Discharge angle
    
    Optional Parameters
    
    ======  =======================================
    key     value
    ======  =======================================
    geo     The class that defines the geometry of the compressor.
    ======  =======================================
    """
    geo=kwargs.get('geo',LoadGeo())
    N_c_max=np.floor((geo.phi_ie-geo.phi_os-pi)/(2*pi))
    return geo.phi_ie-geo.phi_os-2*pi*N_c_max-pi    
    
def Vdisp(geo):
    """ 
    Displacement of the compressor in m^3
    
    Arguments:
        geo : geoVals class
            The class that contains the geometric parameters
    """
    return -2.0*pi*geo.h*geo.rb*geo.ro*(3.0*pi-2.0*geo.phi_ie+geo.phi_i0+geo.phi_o0)

def coords_inv(phi_vec,geo,theta,flag="fi"):
    """ 
    The involute angles corresponding to the points along the involutes
    (fixed inner [fi], fixed scroll outer involute [fo], orbiting
    scroll outer involute [oo], and orbiting scroll inner involute [oi] )
    
    Arguments:
        phi_vec : 1D numpy array
            vector of involute angles
        geo : geoVals class
            scroll compressor geometry
        theta : float
            crank angle in the range 0 to :math: `2\pi`
        flag : string
            involute of interest, possible values are 'fi','fo','oi','oo'
            
    Returns:
        (x,y) : tuple of coordinates on the scroll
    """
    
    pi=math.pi
    phi_i0=geo.phi_i0
    phi_o0=geo.phi_o0
    phi_ie=geo.phi_ie
    rb=geo.rb
    # if a single value is passed in, convert it 
    # to a one-element array
    if not type(phi_vec) is np.ndarray:
        if type(phi_vec) is list:
            phi_vec=np.array(phi_vec)
        else:
            phi_vec=np.array([phi_vec])
    x=np.zeros(np.size(phi_vec))
    y=np.zeros(np.size(phi_vec))
    ro=rb*(pi-phi_i0+phi_o0)
    om=phi_ie-theta+3.0*pi/2.0

    for i in range(len(phi_vec)):
        phi=phi_vec[i]
        if flag=="fi":
            x[i] = rb*cos(phi)+rb*(phi-phi_i0)*sin(phi)
            y[i] = rb*sin(phi)-rb*(phi-phi_i0)*cos(phi)
        elif flag=="fo":
            x[i] = rb*cos(phi)+rb*(phi-phi_o0)*sin(phi)
            y[i] = rb*sin(phi)-rb*(phi-phi_o0)*cos(phi)
        elif flag=="oi":
            x[i] = -rb*cos(phi)-rb*(phi-phi_i0)*sin(phi)+ro*cos(om)
            y[i] = -rb*sin(phi)+rb*(phi-phi_i0)*cos(phi)+ro*sin(om)
        elif flag=="oo":
            x[i] = -rb*cos(phi)-rb*(phi-phi_o0)*sin(phi)+ro*cos(om)
            y[i] = -rb*sin(phi)+rb*(phi-phi_o0)*cos(phi)+ro*sin(om)
        else:
            print "Uh oh... error in coords_inv"
    return (x,y)

def coords_norm(phi_vec,geo,theta,flag="fi"):
    """ 
    The x and y coordinates of a unit normal vector pointing towards
    the scroll involute for the the involutes
    (fixed inner [fi], fixed scroll outer involute [fo], orbiting
    scroll outer involute [oo], and orbiting scroll inner involute [oi])
    
    Arguments:
        phi_vec : 1D numpy array
            vector of involute angles
        geo : geoVals class
            scroll compressor geometry
        theta : float
            crank angle in the range 0 to :math: `2\pi`
        flag : string
            involute of interest, possible values are 'fi','fo','oi','oo'
            
    Returns:
        (nx,ny) : tuple of unit normal coordinates pointing towards scroll wrap
    """
    
    pi=math.pi
    phi_i0=geo.phi_i0
    phi_o0=geo.phi_o0
    phi_ie=geo.phi_ie
    rb=geo.rb
    if not type(phi_vec) is np.ndarray:
        if type(phi_vec) is list:
            phi_vec=np.array(phi_vec)
        else:
            phi_vec=np.array([phi_vec])
    nx=np.zeros(np.size(phi_vec))
    ny=np.zeros(np.size(phi_vec))

    for i in arange(np.size(phi_vec)):
        phi=phi_vec[i]
        if flag=="fi":
            nx[i] = +sin(phi)
            ny[i] = -cos(phi)
        elif flag=="fo":
            nx[i] = -sin(phi)
            ny[i] = +cos(phi)
        elif flag=="oi":
            nx[i] = -sin(phi)
            ny[i] = +cos(phi)
        elif flag=="oo":
            nx[i] = +sin(phi)
            ny[i] = -cos(phi)
        else:
            print "Uh oh... error in coords_norm"
    return (nx,ny)



def circle(xo,yo,r,N=100):
    x=np.zeros(N)
    y=np.zeros(N)
    t=np.linspace(0,2*pi,N)
    for i in arange(N):
        x[i]=xo+r*cos(t[i])
        y[i]=yo+r*sin(t[i])
    return (x,y)
    
def CMMarker(x,y,r,lw=1,fill='k',fill2='w',zorder=4):
    N=25
    (xc,yc)=circle(x,y,r,4*N+1)
    pylab.gca().fill(xc,yc,'w',lw=lw,zorder=zorder)
    
    pylab.gca().fill(np.r_[x,xc[N:2*N+1]],np.r_[y,yc[N:2*N+1]],fill2,zorder=zorder)
    pylab.gca().fill(np.r_[x,xc[3*N:4*N+1]],np.r_[y,yc[3*N:4*N+1]],fill2,zorder=zorder)
    pylab.gca().fill(np.r_[x,xc[0:N+1]],np.r_[y,yc[0:N+1]],fill,zorder=zorder)
    pylab.gca().fill(np.r_[x,xc[2*N:3*N+1]],np.r_[y,yc[2*N:3*N+1]],fill,zorder=zorder)
    


def sortAnglesCCW(t1,t2):
    """
    Sort angles so that t2>t1 in a counter-clockwise sense
    idea from `StackOverflow <http://stackoverflow.com/questions/242404/sort-four-points-in-clockwise-order>`_
    more description: `SoftSurfer <http://softsurfer.com/Archive/algorithm_0101/algorithm_0101.htm>`_

    If the signed area of the triangle formed between the points on a unit circle with angles t1 and t2
    and the origin is positive, the angles are sorted counterclockwise. Otherwise, the angles
    are sorted in a counter-clockwise manner.  Here we want the angles to be sorted CCW, so
    if area is negative, swap angles
    
    Area obtained from the cross product of a vector from origin 
    to 1 and a vector to point 2, so use right hand rule to get 
    sign of cross product with unit length
    """

    if (cos(t1)*sin(t2)-cos(t2)*sin(t1)<0):
        ##Swap angles
        temp=t1;
        t1=t2;
        t2=temp;
    while (t1 > t2):
        ## Make t2 bigger than t1
        t2=t2+2*pi;
    return (t1,t2)

def sortAnglesCW(t1,t2):

    """
    Sort angles so that t2>t1 in a clockwise sense
    idea from `StackOverflow <http://stackoverflow.com/questions/242404/sort-four-points-in-clockwise-order>`_
    more description: `SoftSurfer <http://softsurfer.com/Archive/algorithm_0101/algorithm_0101.htm>`_

    If the signed area of the triangle formed between the points on a unit circle with angles t1 and t2
    and the origin is positive, the angles are sorted counterclockwise. Otherwise, the angles
    are sorted in a counter-clockwise manner.  Here we want the angles to be sorted CCW, so
    if area is negative, swap angles
    
    Area obtained from the cross product of a vector from origin 
    to 1 and a vector to point 2, so use right hand rule to get 
    sign of cross product with unit length
    """

    while (cos(t1)*sin(t2)-sin(t1)*cos(t2)>0):
        ##Swap angles
        temp=t1;
        t1=t2;
        t2=temp;
    #Make t1 between 0 and 2pi
    while (t1<0 or t1> 2.0*pi):
        if t1>2.0*pi:
            t1=t1-2*pi
        else:
            t1=t1+2*pi
    #Want t2 to be less than t1, but no more than 2*pi less
    while (t2<t1 and t1-t2>2*pi):
        t2=t2+2*pi
    while (t2>t1):
        t2=t2-2*pi
    return (t1,t2)

def Shave(geo,theta,shaveDelta):
    phiShave=geo.phi_oe-shaveDelta;
    
    phi=np.linspace(geo.phi_oe-shaveDelta,geo.phi_oe,200)
    (xo,yo)=coords_inv(phi,geo,theta,"oo")
    (xi,yi)=coords_inv(phi,geo,theta,"oi")
    
    z=(1-0.8*(phi-(geo.phi_oe-shaveDelta))/(shaveDelta))
    xnew=z*xo+(1-z)*xi
    ynew=z*yo+(1-z)*yi
    return (xnew,ynew)

def OverlayCVLabels(theta,**kwargs):

    fs=0
    if 'fs' in kwargs:
        fs=kwargs['fs']
    else:
        fs=12
        
    if 'CVList' in kwargs:
        CVList=kwargs['CVList']
    else:
        CVList=['s1','s2','c1','c2','d1','d2']
        
    if 'CVNames' in kwargs:
        CVNames=kwargs['CVNames']
        
    axis=kwargs['axis']
    geo=LoadGeo()
    
    if 's1' in CVList:
        if not 'CVNames' in kwargs:
            label='$s_1$'
        else:
            label=CVNames[CVList.index('s1')]
        phi=np.linspace(geo.phi_ie,geo.phi_ie-theta,100)
        (x_fi,y_fi)=coords_inv(phi,geo,theta,flag="fi")
        phi=np.linspace(geo.phi_oe-pi,geo.phi_ie-pi-theta,100)
        (x_oo,y_oo)=coords_inv(phi,geo,theta,flag="oo")
        x=np.r_[x_fi,x_oo[::-1],(x_fi[0]+x_oo[0])/2.0]
        y=np.r_[y_fi,y_oo[::-1],(y_fi[0]+y_oo[0])/2.0]
        (xc,yc)=MaxIncircle(x,y,100)
        axis.text(xc,yc,label,ha='center',va='center',size=fs)
    
    if 's2' in CVList:
        if not 'CVNames' in kwargs:
            label='$s_2$'
        else:
            label=CVNames[CVList.index('s2')]
        phi=np.linspace(geo.phi_ie,geo.phi_ie-theta,100)
        (x_fi,y_fi)=coords_inv(phi,geo,theta,flag="oi")
        phi=np.linspace(geo.phi_oe-pi,geo.phi_ie-pi-theta,100)
        (x_oo,y_oo)=coords_inv(phi,geo,theta,flag="fo")
        x=np.r_[x_fi,x_oo[::-1],(x_fi[0]+x_oo[0])/2.0]
        y=np.r_[y_fi,y_oo[::-1],(y_fi[0]+y_oo[0])/2.0]
        (xc,yc)=MaxIncircle(x,y,100)
        axis.text(xc,yc,label,ha='center',va='center',size=fs)
    
    if theta<theta_d():
        if 'c2' in CVList:
            if not 'CVNames' in kwargs:
                label='$c_2$'
            else:
                label=CVNames[CVList.index('c2')]
            phi=np.linspace(geo.phi_oe-(theta),geo.phi_oe-theta-2*pi,100)
            (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
            phi=np.linspace(geo.phi_oe-(theta)-pi,geo.phi_oe-pi-theta-2*pi,100)
            (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
            x=np.r_[x_oi,x_fo[::-1]]
            y=np.r_[y_oi,y_fo[::-1]]
            (xc,yc)=MaxIncircle(x,y,100)
            axis.text(xc,yc,label,ha='center',va='center',size=fs)
        
        if 'c1' in CVList:
            if not 'CVNames' in kwargs:
                label='$c_1$'
            else:
                label=CVNames[CVList.index('c1')]
            phi=np.linspace(geo.phi_oe-(theta),geo.phi_oe-theta-2*pi,100)
            (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="fi")
            phi=np.linspace(geo.phi_oe-(theta)-pi,geo.phi_oe-pi-theta-2*pi,100)
            (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="oo")
            x=np.r_[x_oi,x_fo[::-1]]
            y=np.r_[y_oi,y_fo[::-1]]
            (xc,yc)=MaxIncircle(x,y,100)
            axis.text(xc,yc,label,ha='center',va='center',size=fs)
    else:
        if 'd2' in CVList:
            if not 'CVNames' in kwargs:
                label='$d_2$'
            else:
                label=CVNames[CVList.index('d2')]
            phi=np.linspace(geo.phi_oe-(theta),geo.phi_oe-theta-2*pi,100)
            (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
            phi=np.linspace(geo.phi_oe-(theta)-pi,geo.phi_oe-pi-theta-2*pi,100)
            (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
            x=np.r_[x_oi,x_fo[::-1]]
            y=np.r_[y_oi,y_fo[::-1]]
            (xc,yc)=MaxIncircle(x,y,100)
            axis.text(xc,yc,label,ha='center',va='center',size=fs)
        
        if 'd1' in CVList:
            if not 'CVNames' in kwargs:
                label='$d_1$'
            else:
                label=CVNames[CVList.index('d1')]
            phi=np.linspace(geo.phi_oe-(theta),geo.phi_oe-theta-2*pi,100)
            (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="fi")
            phi=np.linspace(geo.phi_oe-(theta)-pi,geo.phi_oe-pi-theta-2*pi,100)
            (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="oo")
            x=np.r_[x_oi,x_fo[::-1]]
            y=np.r_[y_oi,y_fo[::-1]]
            (xc,yc)=MaxIncircle(x,y,100)
            axis.text(xc,yc,label,ha='center',va='center',size=fs)
            
        if 'dd' in CVList:
            if not 'CVNames' in kwargs:
                label='$dd$'
            else:
                label=CVNames[CVList.index('dd')]
            (x1,y1)=(geo.t2_line,geo.m_line*geo.t2_line+geo.b_line)
            (x2,y2)=(-geo.t2_line+geo.ro*cos(geo.phi_ie-pi/2-theta),-(geo.m_line*geo.t2_line+geo.b_line)+geo.ro*sin(geo.phi_ie-pi/2-theta))
            axis.text(0.5*x1+0.5*x2,0.5*y1+0.5*y2,label,ha='center',va='center',size=fs)
    if 'ddd' in CVList:
        if not 'CVNames' in kwargs:
            label='$ddd$'
        else:
            label=CVNames[CVList.index('ddd')]
        (x1,y1)=(geo.t2_line,geo.m_line*geo.t2_line+geo.b_line)
        (x2,y2)=(-geo.t2_line+geo.ro*cos(geo.phi_ie-pi/2-theta),-(geo.m_line*geo.t2_line+geo.b_line)+geo.ro*sin(geo.phi_ie-pi/2-theta))
        axis.text(0.5*x1+0.5*x2,0.5*y1+0.5*y2,label,ha='center',va='center',size=fs,color='k',bbox=dict(facecolor='white', alpha=0.5,boxstyle="round"))
        
def fillS1(theta,**kwargs):
    if 'axis' in kwargs:
        axis=kwargs['axis']
    else:
        axis=pylab.gca()
    if 'color' in kwargs:
        color=kwargs['color']
    else:
        color='b'
    geo=LoadGeo()
    phi=np.linspace(geo.phi_oe,geo.phi_oe-theta,500)
    (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
    phi=np.linspace(geo.phi_oe-pi,geo.phi_oe-pi-theta,500)
    (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
    x=np.r_[x_oi,x_fo[::-1]]
    y=np.r_[y_oi,y_fo[::-1]]
    axis.fill(x,y,color=color)
    return polyarea(x,y)*geo.h

def fillC1(theta,**kwargs):
    if 'axis' in kwargs:
        axis=kwargs['axis']
    else:
        axis=pylab.gca()
    if 'color' in kwargs:
        color=kwargs['color']
    else:
        color='b'
    geo=LoadGeo()
    phi=np.linspace(geo.phi_oe-(theta-2*pi),geo.phi_oe-theta,500)
    (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
    phi=np.linspace(geo.phi_oe-(theta-2*pi)-pi,geo.phi_oe-pi-theta,500)
    (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
    x=np.r_[x_oi,x_fo[::-1]]
    y=np.r_[y_oi,y_fo[::-1]]
    axis.fill(x,y,color=color)
    return polyarea(x,y)*geo.h

def fillD1(theta,**kwargs):
    
    if 'axis' in kwargs:
        axis=kwargs['axis']
    else:
        axis=pylab.gca()   
        
    if 'color' in kwargs:
        color=kwargs['color']
    else:
        color='b'    
    geo=LoadGeo()
    phi=np.linspace(geo.phi_oe-(theta-2*pi),geo.phi_is,500)
    (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
    phi=np.linspace(geo.phi_oe-(theta-2*pi)-pi,geo.phi_os,500)
    (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
    x=np.r_[x_oi,x_fo[::-1]]
    y=np.r_[y_oi,y_fo[::-1]]
    axis.fill(x,y,color=color)
    return polyarea(x,y)*geo.h

def polyarea(x,y):
        
    N=len(x)
    area = 0.0
    for i in range(N):
        j = (i+1) % N
        area = area + x[i]*y[j] - y[i]*x[j]
    return area/2.0
    
def polycentroid(xi,yi):
    # Add additional element if needed to close polygon
    if not xi[0]==xi[-1] or not yi[0]==yi[-1]:
        x=np.r_[xi,xi[-1]]
        y=np.r_[yi,yi[-1]]
    else:
        x=xi
        y=yi
    sumx=0.0
    sumy=0.0
    for i in range(len(x)-1):
        sumx=sumx+(x[i]+x[i+1])*(x[i]*y[i+1]-x[i+1]*y[i])
        sumy=sumy+(y[i]+y[i+1])*(x[i]*y[i+1]-x[i+1]*y[i])
    return sumx/(6*polyarea(x,y)),sumy/(6*polyarea(x,y))
    


def CoordsOrbScroll(theta,geo,shaveOn=True, just_involutes = False):
    shaveDelta=None
    if shaveOn==True:
        shaveDelta=pi/2
    else:
        shaveDelta=1e-16
    (xshave,yshave)=Shave(geo,theta,shaveDelta)
    
    
    phi=np.linspace(geo.phi_is,geo.phi_ie,500)
    (x_oi,y_oi)=coords_inv(phi,geo,theta,flag="oi")
    phi=np.linspace(geo.phi_os,geo.phi_oe-shaveDelta,500)
    (x_oo,y_oo)=coords_inv(phi,geo,theta,flag="oo")
    
    xarc1=geo.xa_arc1+geo.ra_arc1*cos(np.linspace(geo.t2_arc1,geo.t1_arc1,100))
    yarc1=geo.ya_arc1+geo.ra_arc1*sin(np.linspace(geo.t2_arc1,geo.t1_arc1,100))
    xline=np.linspace(geo.t1_line,geo.t2_line,100)
    yline=geo.m_line*xline+geo.b_line
    xarc2=geo.xa_arc2+geo.ra_arc2*cos(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
    yarc2=geo.ya_arc2+geo.ra_arc2*sin(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
    
    ro=geo.rb*(pi-geo.phi_i0+geo.phi_o0)
    om=geo.phi_ie-theta+3.0*pi/2.0
    xarc1_o=-xarc1+ro*cos(om)
    yarc1_o=-yarc1+ro*sin(om)
    xline_o=-xline+ro*cos(om)
    yline_o=-yline+ro*sin(om)
    xarc2_o=-xarc2+ro*cos(om)
    yarc2_o=-yarc2+ro*sin(om)
    
    if just_involutes:
        x=np.r_[x_oo,x_oi[::-1]]
        y=np.r_[y_oo,y_oi[::-1]]
    else:
        x=np.r_[x_oo,xshave,x_oi[::-1],xarc1_o,xline_o,xarc2_o]
        y=np.r_[y_oo,yshave,y_oi[::-1],yarc1_o,yline_o,yarc2_o]
    
    #Output as a column vector
    x=x.reshape(len(x),1)
    y=y.reshape(len(y),1)
    return x,y

def plotScrollSet(theta,geo = None,axis = None, fig = None, lw = None, OSColor = None, show = False, offsetScroll = False, **kwargs):
    """
    The function that plots the scroll sets

    Arguments:
        theta : float
            Crank angle in radians in the range 0 to :math:`2\pi`
            

    Returns:
        OS : matplotlib polygon object for the orbiting scroll

    Optional Parameters
    
    =============    =====================================================
    Variable         Description
    =============    =====================================================
    fig              figure to plot on : default, make new figure
    axis             axis to plot on : default pylab.gca()
    geo              geoVals class with geometric parameters
    discOn           plot the discharge port: True/[False]
    OSColor          color of orbiting scroll: default 'r'
    lw               line width : default 1.0
    discCurves       plot the discharge curves : True/[False]
    shaveOn          shave the end of orb. scroll : True/[False]
    saveCoords       save the coord. of the orb. scroll to file True/[False]
    wallOn           plot the outer wall : [True] /False
    offsetScroll     If true, scrolls are offset : True/[False]
    =============    =====================================================
        

    """

    if axis is None:
        if fig is None:
            fig=pylab.figure(figsize=(5,5))
        axis=fig.add_axes((0,0,1,1))
        
    if geo is None:
        geo=geoVals(rb=0.003522,phi_i0=0.19829,phi_is=4.7,phi_ie=15.5,phi_o0=-1.1248,phi_os=1.8,phi_oe=15.5,h=0.03289)
        setDiscGeo(geo)
        
    if OSColor is not None:
        OSColor=kwargs['OSColor']
    else:
        OSColor='r'
        
    if lw is None:
        lw=1.0
        
    if offsetScroll:
        #Turn off the conventional wall
        kwargs['wallOn'] = False
        #Turn off shaving of the orbiting scroll
        kwargs['shaveOn'] = False
        
        # This is the part of the fixed scroll forming the extension for
        # the offset scroll pocket
        phi  = np.linspace(geo.phi_ie,geo.phi_ie+1.03*pi,1000)
        x,y = coords_inv(phi,geo,0.0,'fi')
        axis.plot(x,y,'k')
#        phi  = np.linspace(geo.phi_ie,geo.phi_ie+1.02*pi,1000)
#        x,y = coords_inv(phi,geo,theta,'oo')
#        axis.plot(x,y,'r--')
        
        # pitch (involute-involute distance for a given involute) 
        # for 2*pi radians or one rotation is equal to 2*pi*rb, subtract 
        # thickness of scroll to get diameter
        # and divide by two to get radius of closing arc for offset region
        r = (2*pi*geo.rb-geo.t)/2.0
        
        xee,yee = coords_inv(phi[-1],geo,0.0,'fi')
        xse,yse = coords_inv(phi[-1]-2*pi,geo,0.0,'fo')
        x0,y0 = (xee+xse)/2,(yee+yse)/2
        
        beta = math.atan2(yee-y0,xee-x0)
        t = np.linspace(beta,beta+pi,1000)
        x,y = x0+r*np.cos(t),y0+r*np.sin(t)
        axis.plot(x,y,'k',lw=lw)
        axis.plot([x[0],x[-1]],[y[0],y[-1]],'b-')
    
    xarc1=geo.xa_arc1+geo.ra_arc1*cos(np.linspace(geo.t2_arc1,geo.t1_arc1,100))
    yarc1=geo.ya_arc1+geo.ra_arc1*sin(np.linspace(geo.t2_arc1,geo.t1_arc1,100))
    xline=np.linspace(geo.t1_line,geo.t2_line,100)
    yline=geo.m_line*xline+geo.b_line
    xarc2=geo.xa_arc2+geo.ra_arc2*cos(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
    yarc2=geo.ya_arc2+geo.ra_arc2*sin(np.linspace(geo.t1_arc2,geo.t2_arc2,100))
    
    ro=geo.rb*(pi-geo.phi_i0+geo.phi_o0)
    om=geo.phi_ie-theta+3.0*pi/2.0
    xarc1_o=-xarc1+ro*cos(om)
    yarc1_o=-yarc1+ro*sin(om)
    xline_o=-xline+ro*cos(om)
    yline_o=-yline+ro*sin(om)
    xarc2_o=-xarc2+ro*cos(om)
    yarc2_o=-yarc2+ro*sin(om)
    
    ##Fixed Scroll
    phi=np.linspace(geo.phi_is,geo.phi_ie,500)
    (x_fi,y_fi)=coords_inv(phi,geo,theta,flag="fi")
    phi=np.linspace(geo.phi_os,geo.phi_oe,500)
    (x_fo,y_fo)=coords_inv(phi,geo,theta,flag="fo")
    
    ## Discharge port
    if 'discOn' in kwargs and kwargs['discOn']==True:
        t=np.linspace(0,2*pi,100)
        x=geo.disc_x0+geo.disc_R*cos(t)
        y=geo.disc_y0+geo.disc_R*sin(t)
        axis.plot(x,y,'k--',lw=lw,zorder=0)
    
    if 'discCurves' in kwargs and kwargs['discCurves']==True:
        (x_fis,y_fis)=coords_inv(geo.phi_os+pi,geo,theta,flag="fi")
        (nx_fis,ny_fis)=coords_norm(geo.phi_os+pi,geo,theta,flag="fi")
        x0=x_fis-nx_fis*geo.ro
        y0=y_fis-ny_fis*geo.ro
        axis.plot(x0,y0,'o')
        axis.plot(x_fis,y_fis,'s')
        t=np.linspace(0,2*pi,200)
        axis.plot(x0+geo.ro*cos(t),y0+geo.ro*sin(t),'-')
        axis.plot(geo.xa_arc1,geo.ya_arc1,'^')
        axis.plot(geo.xa_arc1+geo.ra_arc1*cos(t),geo.ya_arc1+geo.ra_arc1*sin(t),'k--')
    
    if 'wallOn' not in kwargs or kwargs['wallOn']:
        ## Outer Wall
        (x_wall,y_wall)=circle(geo.x0_wall,geo.y0_wall,geo.r_wall,N=200)
        axis.plot(x_wall,y_wall,'k',lw=lw)
        axis.set_xlim([min(x_wall)-0.001,max(x_wall)+0.001])
        axis.set_ylim([min(y_wall)-0.001,max(y_wall)+0.001])
    
    axis.plot(np.r_[xarc1,xline,xarc2],np.r_[yarc1,yline,yarc2],'k',lw=lw)
    axis.plot(x_fi,y_fi,'k',lw=lw)
    axis.plot(x_fo,y_fo,'k',lw=lw)
    axis.plot(np.r_[x_fo[-1],x_fi[-1]],np.r_[y_fo[-1],y_fi[-1]],'k',lw=lw)
    
    shaveOn=None
    if 'shaveOn' in kwargs and kwargs['shaveOn']==False:
        shaveOn=False
    else:
        shaveOn=True
    
    ##Orbiting Scroll
    (XOS,YOS)=CoordsOrbScroll(theta,geo,shaveOn)
    xy=np.hstack((XOS,YOS))
    OrbScroll=pyplot.Polygon(xy,color=OSColor,lw=lw,fill=True,closed=True,ec='k')
    axis.add_patch(OrbScroll)
    
    axis.set_aspect(1.0)
    axis.axis('off')
    
    if 'saveCoords' in kwargs:
        np.savetxt('xos.csv',XOS,delimiter=',')
        np.savetxt('yos.csv',YOS,delimiter=',')
    
    if show:
        pylab.show()
        
    return OrbScroll


class PlotPanel(wx.Panel):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args,**kwds)
        
        size = kwds.pop('size',(400,400))
        self.figure=Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.axes=self.figure.add_subplot(111)
        self.canvas=FigureCanvas(self,wx.ID_ANY,self.figure)

class TaskThread(threading.Thread):
    """Thread that executes a task every N seconds"""
    
    def __init__(self):
        threading.Thread.__init__(self)
        self._finished = threading.Event()
        self._interval = 15.0
    
    def setInterval(self, interval):
        """Set the number of seconds we sleep between executing our task"""
        self._interval = interval
    
    def shutdown(self):
        """Stop this thread"""
        self._finished.set()
    
    def run(self):
        while 1:
            if self._finished.isSet(): return
            self.task()
            
            # sleep for interval or until shutdown
            self._finished.wait(self._interval)
    
    def task(self):
        """The task done by this thread - override in subclasses"""
        raise Exception
        
class PlotThread(TaskThread):

    def setGUI(self,GUI):
        self._GUI=GUI

    def task(self):
        if self._GUI.btn.Value == True:
            wx.CallAfter(self._GUI.plotStep)

class OSCrossSectionPanel(wx.Panel):
    """
    A figure with the cross-section of the scroll wrap
    """
    def __init__(self, parent, dictionary, phiv, h, w):
        wx.Panel.__init__(self, parent)
        
        self.pltpanel = PlotPanel(self, size = (300,300))
        
        # Get the axes
        ax = self.pltpanel.axes
         
        D = 0.1
        ro = dictionary['ro']
        tplate = dictionary['scroll_plate_thickness']
        thrust_ID = dictionary['thrust_ID']
        Ljournal = dictionary['L_crank_bearing']
        journal_IR = dictionary['D_crank_bearing']/2.0
        thrust_IR = thrust_ID/2.0
        tthrust = tplate
        
        ax.fill([-D/2, D/2, D/2, -D/2, -D/2], [-tplate, -tplate, 0, 0, -tplate],'grey')
        
        # The thrust bearing
        ax.fill([-1.5*thrust_IR,-thrust_IR,-thrust_IR,-1.5*thrust_IR,-1.5*thrust_IR],[-tplate-tthrust,-tplate-tthrust,-tplate,-tplate,-tplate-tthrust],'red')
        ax.fill([1.5*thrust_IR,thrust_IR,thrust_IR,1.5*thrust_IR,1.5*thrust_IR],[-tplate-tthrust,-tplate-tthrust,-tplate,-tplate,-tplate-tthrust],'red')
        
        # The journal housing
        ax.fill([-1.5*journal_IR,-journal_IR,-journal_IR,-1.5*journal_IR,-1.5*journal_IR],[-tplate-Ljournal,-tplate-Ljournal,-tplate,-tplate,-tplate-Ljournal],'blue')
        ax.fill([1.5*journal_IR,journal_IR,journal_IR,1.5*journal_IR,1.5*journal_IR],[-tplate-Ljournal,-tplate-Ljournal,-tplate,-tplate,-tplate-Ljournal],'blue')
        
        for phi in phiv:
            phi0 = 0
            rb = 0.003
            y = rb*(sin(phi) - (phi - phi0)*cos(phi))
            ax.fill([y-w/2,y+w/2,y+w/2,y-w/2,y-w/2],[0,0,h,h,0],'grey')
            
        ax.plot([1.5*journal_IR + ro,1.5*journal_IR + ro],[-tplate-Ljournal, -tplate],'b:')
        ax.plot([-1.5*journal_IR + ro, -1.5*journal_IR + ro],[-tplate-Ljournal, -tplate],'b:')
        
        ax.set_aspect('equal')
        ax.axis('off')
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.pltpanel)
        self.SetSizer(sizer)
        sizer.Layout()
        
    def add_wrap(self, pos, w, h):
        pass
        
        

class ScrollAnimForm(wx.Frame):
 
    #----------------------------------------------------------------------
    def __init__(self, geo = None, start = True, size = (400, 400)):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Scroll Model GUI")
 
        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)
        
        import wx.lib.agw.flatmenu as FM
        
        self._mb = FM.FlatMenuBar(panel, wx.ID_ANY, 32, 5)

        layersMenu = FM.FlatMenu()
        
        self.LayerCoordinateAxes = FM.FlatMenuItem(layersMenu, -1, "Show coordinate axes", "Tooltip", wx.ITEM_CHECK)
        self.LayerCoordinateAxes.Check(False)
        self.Bind(FM.EVT_FLAT_MENU_SELECTED, self.OnApplyLayers,id = self.LayerCoordinateAxes.GetId())
        layersMenu.AppendItem(self.LayerCoordinateAxes)
        
        self.LayerOldham = FM.FlatMenuItem(layersMenu, -1, "Oldham ring", "Tooltip", wx.ITEM_CHECK)
        self.LayerOldham.Check(False)
        self.Bind(FM.EVT_FLAT_MENU_SELECTED, self.OnApplyLayers,id = self.LayerOldham.GetId())
        layersMenu.AppendItem(self.LayerOldham)
        
        self.LayerOrbitingScroll = FM.FlatMenuItem(layersMenu, -1, "Orbiting scroll", "Tooltip", wx.ITEM_CHECK)
        self.LayerOrbitingScroll.Check(False)
        self.Bind(FM.EVT_FLAT_MENU_SELECTED, self.OnApplyLayers,id = self.LayerOrbitingScroll.GetId())
        layersMenu.AppendItem(self.LayerOrbitingScroll)
        
        self._mb.Append(layersMenu, "&Layers")
        
        # Create the items
        self.btn = btn = wx.ToggleButton(panel, -1, "Start")
        self.pltpanel = PlotPanel(panel, -1, size=size)
        
        # Do the layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._mb,0,wx.EXPAND)
        sizer.Add(self.btn, 0, wx.ALL|wx.CENTER, 5)
        sizer.Add(self.pltpanel, 0, wx.ALL|wx.CENTER, 5)
        panel.SetSizer(sizer)
        # Bind the events
        btn.Bind(wx.EVT_TOGGLEBUTTON,self.onButton)
        self.Bind(wx.EVT_CLOSE,self.preClose)
        
        self.theta = 0
        self.N = 100
        self.geo = geo
        self.OS = plotScrollSet(0,
                                axis = self.pltpanel.axes,
                                geo = self.geo,
                                lw = 1,
                                discOn = False,
                                offsetScroll = self.geo.phi_ie_offset>0)
        
        self.ax = self.pltpanel.axes
        
        sizer.Layout()
        
        self.SetSize(sizer.GetMinSize())
        
        self.orbiting_layers = []
        if start:
            self.start()
        
    def OnApplyLayers(self, event):
        self.remove_orbiting_layers()
        self.ax.cla()
        self.OS = plotScrollSet(self.theta,
                                axis=self.pltpanel.axes,
                                geo=self.geo,
                                lw=1,
                                discOn=False,
                                offsetScroll = self.geo.phi_ie_offset>0)
        self.apply_stationary_layers()
        self.apply_orbiting_layers(self.theta)

        self.ax.figure.canvas.draw() #Annoyingly this draw is required to flush the ghost orbiting scroll
        
    def apply_stationary_layers(self):
        if self.LayerCoordinateAxes.IsChecked():
            
            self.ax.plot(0, 0, 'k+')
            self.ax.plot([0, 0.01], [0,0], 'k')
            self.ax.plot([0,0], [0.01, 0], 'k')
            self.ax.text(0.01,0,'$x$')
            self.ax.text(0,0.01,'$y$')
            
    def _proj_onto_xd(self, x, y, beta):
        
        # unit vector pointing in the +xbeta direction
        ubeta = np.array([cos(beta),sin(beta)])
        r = np.array([x,y])
        proj = np.dot(r,ubeta)*ubeta
        return proj
    
    def _proj_onto_yd(self, x, y, beta):
        
        # unit vector pointing in the +xbeta direction
        ubeta = np.array([-cos(beta),sin(beta)])
        r = np.array([x,y])
        proj = np.dot(r,ubeta)*ubeta
        return proj
        
    def apply_orbiting_layers(self, theta = 0):
        
        self.remove_orbiting_layers()
        
        def rotated_rectangle(x0,y0,w,h,rot):
            
            x = np.array([-w/2,w/2,w/2,-w/2,-w/2])
            y = np.array([-h/2,-h/2,h/2,h/2,-h/2])
            
            xrot = x*cos(rot)-y*sin(rot)
            yrot = x*sin(rot)+y*cos(rot) 
            
            return xrot+x0, yrot+y0
        
        if self.LayerCoordinateAxes.IsChecked():
            
            om = self.geo.phi_ie-theta+3.0*pi/2.0
            xo = self.geo.ro*cos(om)
            yo = self.geo.ro*sin(om)
            
            self.orbiting_layers.append(self.ax.plot(xo, yo, 'ko')[0])
    
        if self.LayerOldham.IsChecked():
            
            om = self.geo.phi_ie-theta+3.0*pi/2.0
            xo = self.geo.ro*cos(om)
            yo = self.geo.ro*sin(om)
            
            beta = pi/6
            
            OSkeys = [dict(r = 0.04, height = 0.005, width = 0.005, length = 0.005),
                      dict(r = 0.04, height = 0.005, width = 0.005, length = 0.005, betaplus = pi)]
            FSkeys = [dict(r = 0.03, height = 0.005, width = 0.005, length = 0.005),
                      dict(r = 0.03, height = 0.005, width = 0.005, length = 0.005, betaplus = pi)]
            
            for key in OSkeys:
                r = key['r']
                width = key['width']
                length = key['length']
                betaplus = key.get('betaplus',0)
                
                betakey = beta + betaplus + pi/2
                
                xo = self.geo.ro*cos(om)
                yo = self.geo.ro*sin(om)
                
#                xbeta = 0
#                ybeta = -self.geo.ro*cos(om)*sin(beta)+self.geo.ro*sin(om)*cos(beta)
                
                xbeta = self.geo.ro*cos(om)*cos(beta)+self.geo.ro*sin(om)*sin(beta)
                ybeta = 0 
                
                xoffset = xbeta*cos(beta)+ybeta*sin(beta)
                yoffset = xbeta*sin(beta)-ybeta*cos(beta)
                
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),length+3*self.geo.ro,width,beta+pi/2)
                self.orbiting_layers.append(self.ax.fill(x+xo,y+yo,'green', alpha = 0.5)[0])
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),width,length,beta)
                self.orbiting_layers.append(self.ax.fill(x+xoffset,y+yoffset,'k')[0])
                
            for key in FSkeys:
                
                r = key['r']
                width = key['width']
                length = key['length']
                betaplus = key.get('betaplus',0)
                
                betakey = beta + betaplus
                
                xbeta = self.geo.ro*cos(om)*cos(beta)+self.geo.ro*sin(om)*sin(beta)
                ybeta = 0 
                
                xoffset = xbeta*cos(beta)+ybeta*sin(beta)
                yoffset = xbeta*sin(beta)-ybeta*cos(beta)
                
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),length+3*self.geo.ro,width,beta)
                self.orbiting_layers.append(self.ax.fill(x,y,'yellow', alpha = 0.5)[0])
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),width,length,beta)
                self.orbiting_layers.append(self.ax.fill(x+xoffset,y+yoffset,'k')[0])
                
        if self.LayerOrbitingScroll.IsChecked():
            
            om = self.geo.phi_ie-theta+3.0*pi/2.0
            xo = self.geo.ro*cos(om)
            yo = self.geo.ro*sin(om)
            
            beta = pi/6
            
            OSkeys = [dict(r = 0.04, height = 0.005, width = 0.005, length = 0.005),
                      dict(r = 0.04, height = 0.005, width = 0.005, length = 0.005, betaplus = pi)]
            FSkeys = [dict(r = 0.03, height = 0.005, width = 0.005, length = 0.005),
                      dict(r = 0.03, height = 0.005, width = 0.005, length = 0.005, betaplus = pi)]
            
            for key in OSkeys:
                r = key['r']
                width = key['width']
                length = key['length']
                betaplus = key.get('betaplus',0)
                
                betakey = beta + betaplus + pi/2
                
                xo = self.geo.ro*cos(om)
                yo = self.geo.ro*sin(om)
                
                xbeta = self.geo.ro*cos(om)*cos(beta)+self.geo.ro*sin(om)*sin(beta)
                ybeta = 0 
                
                xoffset = xbeta*cos(beta)+ybeta*sin(beta)
                yoffset = xbeta*sin(beta)-ybeta*cos(beta)
                
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),length+3*self.geo.ro,width,beta+pi/2)
                self.orbiting_layers.append(self.ax.fill(x+xo,y+yo,'green', alpha = 0.5)[0])
                x,y = rotated_rectangle(r*cos(betakey),r*sin(betakey),width,length,beta)
                self.orbiting_layers.append(self.ax.fill(x+xoffset,y+yoffset,'k')[0])
            
    def remove_orbiting_layers(self):
        #Clean out all the items from the orbiting layers
        for item in self.orbiting_layers:
            item.remove() # Remove from the GUI
        self.orbiting_layers = []
        
    def start(self):
        """
        Start the plotting machinery
        """
        self.PT=PlotThread()
        self.PT.setDaemon(True)
        self.PT.setGUI(self) #pass it an instance of the frame (by reference)
        self.PT.setInterval(0.05) #delay between plot events
        self.PT.start()
        
    def onButton(self, event):
        """
        Runs the thread
        """
        btn = event.GetEventObject()
        if btn.GetValue()==True:
            btn.SetLabel("Stop")
        else:
            btn.SetLabel("Start")
        
    def updateDisplay(self):
        wx.CallAfter(self._updateDisplay)
    
    def _updateDisplay(self):
        """
        Updates the animation
        """
        if self.Animate==True:
            wx.CallAfter(self.plotStep)
            self.plotThread=threading.Timer(0.001,self.updateDisplay)
            self.plotThread.daemon=True
            self.plotThread.start()

    def plotStep(self):
        
        self.remove_orbiting_layers()
        
        self.theta += 2*np.pi/(self.N-1)
        
        # Plot the orbiting layers
        self.apply_orbiting_layers(self.theta)
        
        #If offset scroll, don't shave the orbiting scroll        
        (x,y)=CoordsOrbScroll(self.theta,
                              self.geo,
                              shaveOn = self.geo.phi_ie_offset < 1e-12
                              )
        
        #Create the data for the orbiting scroll
        self.OS.set_xy(np.hstack((x,y)))
        self.ax.figure.canvas.draw() #Annoyingly this draw is required to flush the ghost orbiting scroll
        self.SetTitle('theta = '+str(self.theta)+' radians')

    def preClose(self,event):
        """
        This runs at the beginning of the closing event to deal with cleanup
        of threads and the GUI
        """
        self.PT.shutdown()
        self.Destroy()

if __name__== "__main__":
    geo = geoVals()
    #Scroll2WRL('Scroll.wrl')
    #plotScrollSet(pi/2,lw=1.0,saveCoords=True)
    
    x, y = CoordsOrbScroll(0, geo, shaveOn = False)
    xo = x - geo.ro*cos(geo.phi_ie-pi/2)
    yo = y - geo.ro*sin(geo.phi_ie-pi/2)
    xf = geo.ro*cos(geo.phi_ie-pi/2) - x
    yf = geo.ro*sin(geo.phi_ie-pi/2) - y
    
    f = open('coordsOS.txt','w')
    last = ''
    old_xy = (9999999999,9999999999999)
    for _x,_y in zip(xo, yo):
        this = '[{x:g}, {y:g}],\n'.format(x = _x[0]*1000, y = _y[0]*1000)
        if (not this == last) and ((old_xy[0]-_x[0])**2+(old_xy[1]-_y[0])**2)**(0.5)>1e-6:
            f.write(this)
        else:
            print this, last
        last = this
        old_xy = _x[0], _y[0]
    f.close()
    
    import textwrap
    
    template = textwrap.dedent(
    """module scroll()
    {{
        linear_extrude(height = {hs:g})
        {{
            polygon([
        
                {polygondata:s}
                
            ]);
        }}
    }}
    
    union()
    {{
        scroll();
        translate([0,0,-10]){{cylinder(r = 75, h = 10, $fn = 300);}}
    }}""")
    
    with open('OSscad.scad','w') as f:
        f.write(template.format(polygondata = open('coordsOS.txt','r').read(),
                          hs = geo.h*1000))
        
    f = open('coordsFS.txt','w')
    last = ''
    old_xy = (9999999999,9999999999999)
    for _x,_y in zip(xf,yf):
        this = '[{x:g}, {y:g}],\n'.format(x = _x[0]*1000, y = _y[0]*1000)
        if (not this == last) and ((old_xy[0]-_x[0])**2+(old_xy[1]-_y[0])**2)**(0.5)>1e-6:
            f.write(this)
        else:
            print this, last
        last = this
        old_xy = _x[0], _y[0]
    f.close()
    
    template = textwrap.dedent(
    """module scroll()
    {{
        linear_extrude(height = {hs:g})
        {{
            polygon([
        
                {polygondata:s}
                
            ]);
        }}
    }}
    
    union()
    {{
        scroll();
        translate([0,0,+90+{hs:g}]){{cylinder(r = 75, h = 10, $fn = 300);}}
    }}""")
    
    with open('FSscad.scad','w') as f:
        f.write(template.format(polygondata = open('coordsFS.txt','r').read(),
                          hs = geo.h*1000))

    for root in ['FSscad','OSscad']:
        subprocess.check_call(['C:\Program Files (x86)\OpenSCAD\openscad.exe','-o',root + '.off',root + '.scad'])
        subprocess.call(['C:\Program Files\VCG\MeshLab\meshlabserver.exe','-i',root + '.off','-o',root + '.x3d'])
    
        def inject(fName, diffuse, specular, MatDEF):
            """
            Parameters
            ----------
            fName : string
            diffuse : string
            specular : string
            """
            
            injected_string = textwrap.dedent(
            """
            <Appearance>
                <Material id='{MatDEF:s}' DEF='{MatDEF:s}' diffuseColor='{diffuse:s}' specularColor='{specular:s}' />
            </Appearance>
            """.format(MatDEF = MatDEF,
                                    diffuse = diffuse, 
                                    specular = specular)
            )
            
            lines = open(fName,'r').readlines()
            
            iLine = -1
            for i,line in enumerate(lines):
                if line.find('<Shape>') > -1:
                    iLine = i
                    break
            
            lines.insert(iLine+1, injected_string.strip())
            
            with open(fName,'w') as f:
                f.write(''.join(lines))
            
        inject(root + '.x3d', diffuse = '0.8 0.8 0.8', specular = '0.2 0.2 0.2', MatDEF = 'scrollMat')
        
#    pylab.fill(x,y)
#    pylab.show()
##     pylab.show()
    pass
    
