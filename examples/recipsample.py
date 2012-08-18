from __future__ import division
from math import pi
from time import clock
import sys, os

# If the following line is uncommented, python will try to use a local version
# of PDSim.  This is handy for debugging purposes.  Generally you want this line 
# commented out
sys.path.insert(0, os.path.abspath('..'))

from PDSim.flow.flow import FlowPath
from PDSim.flow import flow_models
from PDSim.core.containers import ControlVolume
from PDSim.core.core import Tube,PDSimCore
from PDSim.plot.plots import debug_plots
from PDSim.misc._listmath import listm
from CoolProp import State
from CoolProp import CoolProp as CP
from PDSim.flow.flow_models import ValveModel
from PDSim.recip.core import Recip
    
def Compressor():

    recip=Recip()
    
    recip.piston_stroke = 0.02   #Piston stroke, m
    recip.piston_diameter = 0.02   #Piston diameter, m
    recip.piston_length = 0.02   #Piston Length, m
    recip.omega = 377       #Frequency, rad/sec (60Hz)
    recip.crank_length = 0.01      #length of crank, m
    recip.connecting_rod_length = 0.04      #length of connecting rod, m
    recip.x_TDC = 0.003 #Distance to the TDC position of the piston from the valve plate

    recip.d_discharge=0.0059;  #discharge port diameter in meters
    recip.d_suction=recip.d_discharge; #suction diameter in meters
        
    #These are parameters needed for the ambient heat transfer model
    recip.h_shell = 0.010 #[kW/m2/K]
    recip.A_shell = pi*10*2*(0.0254**2) #[m2]
    recip.Tamb = 298 #[K]
    
    recip.mu_oil = 0.0086
    recip.delta_gap = 10e-6
    recip.eta_motor = 0.95
    
    recip.shell_volume = 100e-6
    #Calculate Vdisp
    recip.pre_solve()
    
    Ref='R410A'
    inletState=State.State(Ref,dict(T=289.15, D=33.1))
    p_outlet = inletState.p*2.5
    T2s = recip.isentropic_outlet_temp(inletState,p_outlet)
    outletState=State.State(Ref,{'T':T2s,'P':p_outlet})
    mdot_guess = inletState.rho*recip.Vdisp()*recip.omega/(2*pi)
    
    #First add the control volumes.
    recip.add_CV( ControlVolume(key='A',
                               initialState=outletState.copy(),
                               VdVFcn=recip.V_dV,
                               becomes='A') )
    recip.add_CV( ControlVolume(key='shell',
                               initialState=inletState.copy(),
                               VdVFcn=recip.V_shell,
                               becomes='shell') )
    
    recip.add_tube( Tube(key1='inlet.1',key2='inlet.2',L=0.03,ID=0.02,
                             mdot=mdot_guess, State1=inletState.copy(),
                             fixed=1,TubeFcn=recip.TubeCode) )
    recip.add_tube( Tube(key1='outlet.1',key2='outlet.2',L=0.03,ID=0.02,
                             mdot=mdot_guess, State2=outletState.copy(),
                             fixed=2,TubeFcn=recip.TubeCode) )
    
    recip.add_flow(FlowPath(key1='shell', key2='inlet.2', MdotFcn=recip.Inlet))
    recip.add_flow(FlowPath(key1='shell', key2='A', MdotFcn=recip.Suction))
    recip.add_flow(FlowPath(key1='outlet.1', key2='A', MdotFcn=recip.Discharge))
    recip.add_flow(FlowPath(key1='shell', key2='A', MdotFcn=recip.PistonLeakage))

    E = 1.93e11             #Youngs Modulus, [Pa]
    h_valve = 0.0001532     #Valve thickness, [m]
    l_valve = 0.018         #Total length of valve, [m]
    a_valve = 0.0140        #Distance from anchor to force, [m]
    rho_valve = 8000        #Density of spring steel, [kg/m^3] 
    C_D = 1.17              #Drag coefficient [-]
    d_valve = 0.007         #Valve Diameter [m]
    x_stopper = 0.0018      #Stopper location [m]
    
    #The suction valve parameters
    recip.suction_valve=ValveModel(
          d_valve=d_valve,
          d_port=recip.d_suction,
          C_D=C_D,
          h_valve=h_valve,
          a_valve=a_valve,
          l_valve=l_valve,
          rho_valve=rho_valve,
          E=E,
          x_stopper=x_stopper,
          key_up='inlet.2',
          key_down='A'
          )
    recip.add_valve(recip.suction_valve)
    #The discharge valve parameters
    recip.discharge_valve=ValveModel(
          d_valve=d_valve,
          d_port=recip.d_discharge,
          C_D=C_D,
          h_valve=h_valve,
          a_valve=a_valve,
          l_valve=l_valve,
          rho_valve=rho_valve,
          E=E,
          x_stopper=x_stopper,
          key_up='A',
          key_down='outlet.1'
          )
    recip.add_valve(recip.discharge_valve)

    recip.EulerN = 5000
    recip.HeunN = 3000
    recip.RK45_eps = 1e-10
    t1=clock()
    
    recip.precond_solve(key_inlet='inlet.1',key_outlet='outlet.2',
                endcycle_callback=recip.endcycle_callback,
                heat_transfer_callback=recip.heat_transfer_callback,
                lump_energy_balance_callback = recip.lump_energy_balance_callback,
                valves_callback =recip.valves_callback,
                solver_method = 'Euler',
                OneCycle = False,
                UseNR = True,
                )
    print 'time taken', clock()-t1
    
    debug_plots(recip)
    
if __name__=='__main__':    
    Compressor()

    