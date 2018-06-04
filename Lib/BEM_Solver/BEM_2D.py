#########################################################################
#       (C) 2017 Department of Petroleum Engineering,                   # 
#       Univeristy of Louisiana at Lafayette, Lafayette, US.            #
#                                                                       #
# This code is released under the terms of the BSD license, and thus    #
# free for commercial and research use. Feel free to use the code into  #
# your own project with a PROPER REFERENCE.                             #
#                                                                       #
# PYBEM2D Code                                                          #
# Author: Bin Wang                                                      # 
# Email: binwang.0213@gmail.com                                         # 
# Reference: Wang, B., Feng, Y., Berrone, S., et al. (2017) Iterative   #
# Coupling of Boundary Element Method with Domain Decomposition.        #
# doi:                                                                  #
#########################################################################

'''BEM 2D Module
-BEM_2D.py		        #Mainfunction(Mesh,BC,Solve,Plot)
-BEM_Elements.py        #BEM Element main class
 -Constant_element.py       #Constant element module
 -Linear_element.py         #Linear element module
 -Quadratic_element.py      #Quadratic element module
 -Constant_element_Trace.py #Constant element with internal trace module
 -Quadratic_element_Trace.py#Quadratic element with internal trace module
 -ShapeFunc.py              #Shape function in kernel integration
'''

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.size': 12}) #font

#[BEM Element type]
from .Elements.BEM_Elements import BEM_element
from .Elements.Quadratic_element import *
from .Elements.Linear_element import *
from .Elements.Constant_element import *

from .Elements.Constant_element_Trace import *
from .Elements.Quadratic_element_Trace import *


#[General Geometry Lib]
from Lib.Tools.Geometry import *

###############################
#
#  Core BEM 2D Class
#
###############################

class BEM2D:
    """Contains information and functions related to a 2D potential problem using BEM."""
        
    def __init__(self):
        """Creates a BEM objecti with some specific paramters
        
        Arguments
        ---------
        [Discretization]
        Pts_e     -- Boundary end nodes for abritary shape Polygon. 
                     e.g. Boundary_vert=[(0.0, 0.0), (0.0, 1.5), (1.0, 1.5), (1.5, 0.0)]
        Pts_t     -- Internal trace end node for abritary intersection 
                     e.g. Trace_vert=[((0.25, 0.5), (1.25, 0.5)),((0.25, 1.2), (1.25, 1.2))]
        
        Ne_edge     -- Number of element on all edges
        Ne_trace    -- Number of element on all traces
        Nedof_edge  -- Number of DOF for edge elements (const=1 linear=2 quad=3)
        Nedof_trace -- Number of DOF for trace elements
        Ndof_edge   -- Total number of DOF for all edge elements
        Ndof_trace  -- Total number of DOF for all trace elements
        Ndof        -- Total number of DOF for all elements 

        [BEM Solver]
        TraceOn         -- Enable the internal (geometry) trace
        BEs_edge        -- BEM element collection for boundary edge
        BEs_trace       -- BEM element collection for internal edge
        NumE_bd         -- the number of element on each boundary
        NumE_t          -- the number of element on each trace

        domain_min      -- minimum coords of a domain 
        domain_max      -- maxmum coords of a domain

        h_edge    -- Length of element for boundary edge [optional]
        h_trace   -- Length of element for trace [optional]
        Num_boundary -- Number of boundary edge elements
        Num_trace    -- Number of trace elements
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        self.Pts_e=[]
        self.Pts_t=[]
        
        self.domain_min=[] #Additional Geometory variable
        self.domain_max=[]
        
        self.Ne_edge=0
        self.Ne_trace=0
        self.Nedof_edge=0
        self.Nedof_trace=0
        self.Ndof_edge=0
        self.Ndof_trace=0
        self.Ndof=0
        self.h_edge=0
        self.h_trace=0
        
        self.TraceOn=0
        
        self.Num_boundary=1
        self.Num_trace=1
        
        self.BEs_edge=[]
        self.BEs_trace=[]
        self.NumE_bd=[]
        self.NumE_t=[]

        #Nice reference of BC https://www.comsol.com/blogs/how-to-make-boundary-conditions-conditional-in-your-simulation/
        self.TypeE_edge="Quad"
        self.TypeE_trace="Const"
        self.NeumannBC=[]
        self.DirichletBC=[]
        self.RobinBC=[]
        
        #[BEM Mesh Info]
        self.mesh_nodes=[] #All of bem nodes for each edge


    ###########Meshing Module##############
    def Append_Line(self,Pts_a=(0,0),Pts_b=(0,0),Nbd=1,panels=[],bd_marker=0,Type="Quad"):
        """Creates a BE along a line boundary. Anticlock wise, it decides the outward normal direction
           This can be used to create abritary polygon shape domain

        Arguments
        ---------
        xa, ya -- Cartesian coordinates of the first start-point.

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        
        if (Type=="Quad"): 
            #Quadratic element of additional point
            Nbd=Nbd*2
        
        Pts=EndPointOnLine(Pts_a,Pts_b,Nseg=Nbd,refinement="linspace")
        
        if (Type=="Const" or Type=="Linear"):
             for i in range(Nbd):
                #[0,1]  [1,2]
                Node1=Pts[i]
                Node2=Pts[i+1]
                panels.append(BEM_element(Node1,[],Node2,Type,bd_marker))#Neumann, Dirchlet    
        
        if (Type=="Quad"):
            #To get coordinates of additional one node for a Quadratic BE
            Nbd=int(Nbd/2)
            for i in range(Nbd):
                #[0,1,2]  [2,3,4]
                Node1=Pts[2*i]
                Node2=Pts[2*i+1]
                Node3=Pts[2*i+2]
                panels.append(BEM_element(Node1,Node2,Node3,Type,bd_marker))#Neumann, Dirchlet
        return Pts
     
    def set_Mesh(self,Pts_e=[],Pts_t=[],He_edge=0.1,He_trace=0.1,Type='Quad',mode=0):
        """Create BEM mesh based on either number of element or length of element
           Support for:
           1. Constant element,linear element and Quadratic element
           2. Abritary closed shape by giving boundary vertex(Pts_e)
           3. Internal line segments by giving internal vertex(Pts_t)
        
        
        Arguments
        ---------
        Ne_edge   -- Number of element in boundary edge [optional]
        Ne_trace  -- Number of element in trace [optional]
        h_edge    -- Length of element for boundary edge [optional]
        h_trace   -- Length of element for trace [optional]
        mode      -- 0-round up connect 1-manully set up 
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        
        self.Pts_e=Pts_e
        self.Pts_t=Pts_t
        self.Num_boundary=len(Pts_e)
        self.Num_trace=len(Pts_t)
        self.h_edge=He_edge
        self.h_trace=He_trace
        
        #find the domain min,max for plotting
        self.domain_min=(min(np.asarray(self.Pts_e)[:,0]),min(np.asarray(self.Pts_e)[:,1]))
        self.domain_max=(max(np.asarray(self.Pts_e)[:,0]),max(np.asarray(self.Pts_e)[:,1]))        
        
        #Boundary mesh
        self.TypeE_edge=Type
        for i in range(self.Num_boundary):
            Node=self.Pts_e[i]
            if (i==self.Num_boundary-1):
                if(mode==0): Node_next=self.Pts_e[0] #round connect
                elif(mode==1): break#manully connect
            else: 
                Node_next=self.Pts_e[i+1]
            Ne_edge=int(np.ceil(calcDist(Node,Node_next)/self.h_edge))
            self.NumE_bd.append(Ne_edge)
            
            added_nodes=self.Append_Line(Node,Node_next,Ne_edge,self.BEs_edge,bd_marker=i,Type=Type)
            self.mesh_nodes.append(added_nodes)
        
        #Additional mesh info
        self.Ne_edge=len(self.BEs_edge)
        if(self.TypeE_edge=="Const"):
            self.Ndof_edge = 1 * self.Ne_edge
            self.Nedof_edge=1
        elif(self.TypeE_edge == "Linear"):
            self.Ndof_edge = 1 * self.Ne_edge
            self.Nedof_edge=2
        else:
            self.Ndof_edge = 2*self.Ne_edge
            self.Nedof_edge=3
        
        #Trace mesh
        self.TypeE_trace="Const"
        if (He_trace != None and len(Pts_t)!=0):
            self.TraceOn=1 #
            print('We have trace')
            for i in range(self.Num_trace):
                Node,Node_next=self.Pts_t[i][0],self.Pts_t[i][1]
                Ne_trace=int(np.ceil(calcDist(Node,Node_next)/self.h_trace))
                self.NumE_t.append(Ne_trace)
                
                temp_trace=[]
                added_nodes=self.Append_Line(Node,Node_next,Ne_trace,temp_trace,bd_marker=self.Num_boundary+i,Type="Const")#fracture always 0 flux on edge
                self.BEs_trace.append(temp_trace)
                
                self.mesh_nodes.append(added_nodes)
        #Additional mesh info
        self.Ne_trace=sum(self.NumE_t)
        self.Nedof_trace = 1
        self.Ndof_trace=self.Ne_trace

        #Total DOF
        self.Ndof=self.Ndof_edge+self.Ndof_trace

        if(self.Ndof_trace == 0):
            self.TraceOn = 0
        else:
            self.TraceOn = 1

        #Plot Mesh
        print('Total DOF=',self.Ndof)
        self.plot_Mesh()


    ###########Boundary Conditions Module#################
    def set_BoundaryCondition(self,DirichletBC=[],NeumannBC=[],RobinBC=[],update=0,mode=0,Robin_a=1):
        """Set up boundary conditions for generated bem mesh using element marker
           Dirichlet or Neumann boundary can be applied for each edge or trace
        
        Input format:
            Dirichelt[(element marker,BC_value)]
            BC_value
        1. The default BC is no-flow Neumann boundary condition
        2. Support for const boundary condition assignment(mode-0)
        3. Support for non-constant(node-wise) boundary condition assignment(mode-1)
        4. mode 1 currently only support for boundary edge
           
        Arguments
        ---------
        DirichletBC   -- Dirichlet boundary condition for a specifc edge, id=0
        NeumannBC     -- Neumann boundary condition for a specific edge, id=1
        RobinBC       -- Robin boundary condition for a specific edge, id=2
        update        -- model selection, 0-set up new BCs 1-update old BCs, normally used for DDM
        mode          -- mode0 constant BC assignmetn  mode1 node-wise BC assignment, normally used for DDM
        Robin_a       -- Robin coefficient
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """

        #Reset all element's BC as no-flow BC
        if(update==0):
            #Store BC as original BC when new BC created
            self.DirichletBC=DirichletBC
            self.NeumannBC=NeumannBC
            self.RobinBC=RobinBC
            for i in range(len(self.BEs_edge)):
                self.BEs_edge[i].reset_Element()
            for i in range(len(self.BEs_trace)):
                for j in range(len(self.BEs_trace[i])):
                    self.BEs_trace[i][j].reset_Element()

        #Loop for three boundary conditions
        for BCid in range(3):
            BCs=[]
            if(BCid==0 and len(DirichletBC)!=0):
                BCs=DirichletBC
            if(BCid==1 and len(NeumannBC)!=0):
                BCs=NeumannBC
            if(BCid==2 and len(RobinBC)!=0):
                BCs=RobinBC
            #Dirichelt BC
            for i in range(len(BCs)):
                bd_markerID=BCs[i][0]
                elementID=self.bdmarker2element(bd_markerID)
                for j in range(len(elementID)):
                    if(bd_markerID>self.Num_boundary-1):#this is a trace
                        tID=elementID[j][0]
                        eID=elementID[j][1]
                        #Special case of flux constrain for the first time BC setup
                        if(BCid==1 and update==0): #Flux should be average flux strength per unit length                           
                            average_Q = BCs[i][1] / len(self.BEs_trace[tID])
                            length_trace = calcDist(self.Pts_t[tID][0], self.Pts_t[tID][1])
                            average_Q = average_Q * length_trace
                            # Neumann-1   Dirichlet-0 Robin-2
                            self.BEs_trace[tID][eID].set_BC(BCid, average_Q, Robin_a)
                        #General case with Dirichlet
                        else:
                            if(mode==0):
                                self.BEs_trace[tID][eID].set_BC(BCid,BCs[i][1],Robin_a) # Neumann-1   Dirichlet-0 Robin-2
                            elif(mode==1):

                                bd_values=self.bd2element(self.TypeE_trace,eleid=j,node_values=BCs[i][1])
                                self.BEs_trace[tID][eID].set_BC(BCid,bd_values,Robin_a,mode=1)
                    else:#this is a edge element
                        eID=elementID[j]
                        if(mode==0):
                            self.BEs_edge[eID].set_BC(BCid,BCs[i][1],Robin_a) # Neumann-1   Dirichlet-0 Robin-2
                        elif(mode==1):
                            bd_values=self.bd2element(self.TypeE_edge,eleid=j,node_values=BCs[i][1])
                            self.BEs_edge[eID].set_BC(BCid,bd_values,Robin_a,mode=1)


    def print_debug(self):
        """Check Meshing and B.C for different type of elements
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        #Check Meshing and B.C for different type of elements
        print("[Mesh] State")
        print("Number of boundary elements:%s" % (len(self.BEs_edge)+len(self.BEs_trace)))
        print("Edge Num.:%s" %(self.Num_boundary))
        print("# Neumann-1   Dirichlet-0")
        print("(E)Pts\tX\tY\tType\tMarker\t\tBC_type\t\tBC_value")
        for i, pl in enumerate(self.BEs_edge):
            eleid = i + 1
            for j in range(self.Nedof_edge):
                nodeid = self.getNodeId(i, j,'Edge') + 1
                print("(%s)%s\t%5.3f\t%.3f\t%.4s\t%d\t\t%d\t\t%.3f" %
                        (eleid, nodeid, pl.xc, pl.yc, pl.element_type, pl.bd_marker, pl.bd_Indicator, pl.bd_value1))

        print("Trace Num.:%s" %(self.Num_trace))
        eleid = 0
        for i in range(self.Num_trace):
            print("--Trace ",i+1)
            for j, pl in enumerate(self.BEs_trace[i]):
                for k in range(self.Nedof_trace):
                    global_eleid = eleid + self.Ne_edge + 1
                    global_index = self.getNodeId(eleid, k,'Trace') + 1
                    #print("(%s)%s\t%5.3f\t\t%.3f\t\t%.4s\t\t%d" % (index,2*len(self.BEs_edge)+index,pl.xa,pl.ya,pl.element_type,pl.bd_marker))
                    print("(%s)%s\t%5.3f\t%.3f\t%.4s\t%d\t\t%d\t\t%.3f" % 
                          (global_eleid, global_index, pl.xc, pl.yc, pl.element_type, pl.bd_marker, pl.bd_Indicator, pl.bd_value1))
                
                eleid = eleid + 1



    ###########Matrix Assemble and Solve Module#################
    def Solve(self,DDM=0,AB=[]):
        """Build up and solve BEM matrix using collocation method
        
        #Reference: BEM Introduction Course-1991-P81
        #Trace-Reference: A BEM solution of steady-state ﬂow problems in discrete fracture networks with minimization of core storage
        
        DDM--Domain Decomposion Solution, 1=DDM 0=general
        AB--Input HG matrix for DDM

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        debug=0

        if (self.TraceOn==1):#Internal Trace ON
            if(self.TypeE_edge == 'Const'):#Support any type of boundary conditions
                Ab=build_matrix_const_Trace(self.BEs_edge,self.BEs_trace,self,DDM,AB)
                X = np.linalg.solve(Ab[0], Ab[1])  # linear solution X
                solution_allocate_const_Trace(self.BEs_edge, self.BEs_trace, X, self)
                return Ab

            if(self.TypeE_edge == 'Quad'): #Only support zero flux boundary conditions
                Ab=build_matrix_quadratic_Trace(self.BEs_edge,self.BEs_trace,self)
                X = np.linalg.solve(Ab[0], Ab[1])  # linear solution X
                solution_allocate_quadratic_Trace(self.BEs_edge, self.BEs_trace, X, self)
                return Ab

        else:#Boundary Only Case
            if (self.TypeE_edge=="Quad"): #2nd order element
                Ab=build_matrix_quadratic(self.BEs_edge,DDM,AB) #matrix AB
                X = np.linalg.solve(Ab[0], Ab[1])#linear solution X
                solution_allocate_quadratic(self.BEs_edge,X,debug)#assign solution back to element class
                return Ab
            
            if (self.TypeE_edge=="Linear"):#linear element
                Ab = build_matrix_linear(self.BEs_edge, DDM, AB)  # matrix AB
                X = np.linalg.solve(Ab[0], Ab[1])#linear solution X
                solution_allocate_linear(self.BEs_edge,X,debug)#assign solution back to element class
                return Ab
            
            if (self.TypeE_edge=="Const"):#const element
                Ab = build_matrix_const(self.BEs_edge, DDM, AB)  # matrix AB
                X = np.linalg.solve(Ab[0], Ab[1])#linear solution X
                #print(X)
                solution_allocate_constant(self.BEs_edge,X,debug)#assign solution back to element class
                return Ab
            
            return Ab
        

    
    def get_Solution(self,Pts,bd_markerID=-1):
        """Get the solution variable(p,ux,uy) at any given Point(Pts)
           Reference: BEM Introduction Course-1991
           Reference: A BEM solution of steady-state ﬂow problems in discrete fracture networks with minimization of core storage
        
        Arguments
        ---------
        Pts_location -- the element index which Pts belongs to (-1 internal, 1 element, 2 edge connection node)
        Pts          -- query points
        bd_markerID  -- [optional] boundary marker id which helps to determine the solution on edge connection point

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        Pts_location=self.point_on_element(Pts) #check point location

        if (self.TraceOn==1):#DFN function ON
            if(Pts_location == -1):  # Pts is a internal point
                if(self.TypeE_edge == 'Const'):
                    return Field_Solve_const_Trace(Pts[0], Pts[1], self.BEs_edge, self.BEs_trace)
                else:
                    return Field_Solve_quadratic_Trace(Pts[0], Pts[1], self.BEs_edge, self.BEs_trace)
            elif(len(Pts_location) == 1):  # Pts is located on boundary element
                if(self.TypeE_edge == 'Const'):
                    return Field_Solve_const_Trace(Pts[0], Pts[1], self.BEs_edge, self.BEs_trace, elementID=Pts_location[0])
                else:
                    return Field_Solve_quadratic_Trace(Pts[0], Pts[1], self.BEs_edge, self.BEs_trace, elementID=Pts_location[0])
        
        if (self.TypeE_edge=="Quad"): #2nd order element
            if(Pts_location==-1): #Pts is a internal point
                return Field_Solve_quadratic(Pts[0], Pts[1], self.BEs_edge)
            elif(len(Pts_location)==1):#Pts is located on boundary element
                return Field_Solve_quadratic(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
            elif(len(Pts_location)==2):#Pts is located on the edge connection point(among Pts_e)
                if(bd_markerID!=-1):
                    for id in Pts_location:
                        if(self.element2edge(id)==bd_markerID):
                            eleid=id
                    #print(Pts_location,eleid,bd_markerID)
                    return Field_Solve_quadratic(Pts[0], Pts[1], self.BEs_edge,elementID=eleid)
                else:
                    return Field_Solve_quadratic(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
                       #,Field_Solve_quadratic(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[1])]
        
        if (self.TypeE_edge=="Linear"):#linear element
            if(Pts_location==-1): #Pts is a internal point
                return Field_Solve_linear(Pts[0], Pts[1], self.BEs_edge)
            elif(len(Pts_location)==1):#Pts is located on boundary element
                return Field_Solve_linear(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
            elif(len(Pts_location)==2):#Pts is located on the edge connection point(among Pts_e)
                if(bd_markerID!=-1):
                    for id in Pts_location:
                        if(self.element2edge(id)==bd_markerID):
                            eleid=id
                    return Field_Solve_linear(Pts[0], Pts[1], self.BEs_edge,elementID=eleid)
                else:
                    return Field_Solve_linear(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
                       #,Field_Solve_linear(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[1])]
        
        if (self.TypeE_edge=="Const"):
            if(Pts_location==-1): #Pts is a internal point
                return Field_Solve_constant(Pts[0], Pts[1], self.BEs_edge)
            elif(len(Pts_location)==1):#Pts is located on boundary element
                return Field_Solve_constant(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
            elif(len(Pts_location)==2):#Pts is located on the edge connection point(among Pts_e)
                if(bd_markerID!=-1):
                    for id in Pts_location:
                        if(self.element2edge(id)==bd_markerID):
                            eleid=id
                    return Field_Solve_constant(Pts[0], Pts[1], self.BEs_edge,elementID=eleid)
                else:#always take the value from the first element
                    return Field_Solve_constant(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[0])
                       #,Field_Solve_constant(Pts[0], Pts[1], self.BEs_edge,elementID=Pts_location[1])]

    def print_solution(self):
        """Check Meshing and B.C for different type of elements
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: May. 2018
        """
        #Check Meshing and B.C for different type of elements
        print("[Mesh] State")
        print("Number of boundary elements:%s" %
              (len(self.BEs_edge) + len(self.BEs_trace)))
        print("Edge Num.:%s" % (self.Num_boundary))
        print("# Neumann-1   Dirichlet-0")
        print("(E)Pts\tP\tQ\tU\tV")

        mass_balance=0

        for i, pl in enumerate(self.BEs_edge):
            eleid = i + 1
            P, Q = pl.get_PQ()
            U,V =pl.get_U(),pl.get_V()
            for j in range(self.Nedof_edge):
                nodeid = self.getNodeId(i, j, 'Edge') + 1
                print("(%s)%s\t%.2f\t%.2f\t%.2f\t%.2f" % (eleid, nodeid, P[j], Q[j],U[j],V[j]))
                mass_balance = mass_balance + Q[j]*pl.length # Mass balance should be the unit strength
        mass_e = mass_balance
        
        print('Unit Boundary Flux', mass_e)
        print("Trace Num.:%s" % (self.Num_trace))
        eleid = 0
        for ti in range(self.Num_trace):
            print("--Trace ", i + 1)
            for i, pl in enumerate(self.BEs_trace[ti]):
                P, Q = pl.get_PQ()
                for j in range(self.Nedof_trace):
                    global_eleid = eleid + self.Ne_edge + 1
                    global_index = self.getNodeId(eleid, j, 'Trace') + 1
                    #print("(%s)%s\t%5.3f\t\t%.3f\t\t%.4s\t\t%d" % (index,2*len(self.BEs_edge)+index,pl.xa,pl.ya,pl.element_type,pl.bd_marker))
                    print("(%s)%s\t%.2f\t%.2f\t%.2f\t%.2f" %
                          (global_eleid, global_index, P[j], Q[j], U[j], V[j]))
                    mass_balance = mass_balance + Q[j]
                eleid = eleid + 1
        mass_t = mass_balance - mass_e
        print('Unit Trace Flux', mass_t)
        print('Mass Balance=', mass_balance,abs(mass_e/mass_t))

    ###########Post-processing Module#################
    def get_BDSolution(self,bd_markerID):
        """Get the solution variable(p,ux,uy) at all nodes on any given boundary (bd_markerID)
           normally used for iterative solver
           
        Arguments
        ---------
        bd_markerID  -- boundary marker id

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        p=[]#pressure,p
        q=[]#flux,dp/dn
        u=[]#flux in x direction,dp/dx
        v=[]#flux in y direction,dp/dy

        elementID=self.bdmarker2element(bd_markerID)#find the element idx on this edge

        if (bd_markerID>self.Num_boundary-1):#this is a trace
            ti = elementID[0][0]
            for ei, pl in enumerate(self.BEs_trace[ti]):
                temp = pl.get_PQ()
                p=p+temp[0]
                q=q+temp[1]
                u=u+pl.get_U()
                v=v+pl.get_V()
        
        else:#this is a boundary edge
            for i in range(len(elementID)):#loop for all elements on this edge
                ele=self.BEs_edge[elementID[i]]
                if (self.TypeE_edge=="Const"):
                    p.append(ele.P1)
                    q.append(ele.Q1)
                    u.append(ele.u1)
                    v.append(ele.v1)
                if (self.TypeE_edge=="Linear"):
                    p.append(ele.P1)
                    q.append(ele.q1)
                    u.append(ele.u1)
                    v.append(ele.v1)
                    if (i==len(elementID)-1):
                        p.append(ele.P2)
                        q.append(ele.q2)
                        u.append(ele.u2)
                        v.append(ele.v2)
                if(self.TypeE_edge=="Quad"):
                    p.extend((ele.P1,ele.P2))
                    q.extend((ele.Q1,ele.Q2))
                    u.extend((ele.u1,ele.u2))
                    v.extend((ele.v1,ele.v2))
                    if (i==len(elementID)-1):
                        p.append(ele.P3)
                        q.append(ele.Q3)
                        u.append(ele.u3)
                        v.append(ele.v3)

        #darcy flow, velcoity=-dp/dx
        p=np.array(p)
        q=np.array(q)
        u=np.array([-i for i in u])
        v=np.array([-i for i in v])
        return p,q,u,v


    ###########Visulation Module################
    def plot_Mesh(self,Annotation=1):
        """Plot BEM Mesh

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        #x_min, x_max = min(self.Pts_e)[0],max(self.Pts_e)[0]
        #y_min, y_max = min(self.Pts_e)[1],max(self.Pts_e)[1]
        x_min, x_max =self.domain_min[0],self.domain_max[0]
        y_min, y_max =self.domain_min[1],self.domain_max[1]
        
        space=0.1*calcDist((x_min,y_min),(x_max,y_max))
        
        #plt.figure(figsize=(4, 4))
        plt.axes().set(xlim=[x_min-space, x_max+space],
                       ylim=[y_min-space, y_max+space],aspect='equal')

        #Domain boundary
        #plt.plot(*np.asarray(self.Pts_e).T,lw=1,color='black')
        #plt.scatter(*np.asarray(self.Pts_w).T,s=20,color='red')
        
        #Boundary elements
        plt.plot(np.append([BE.xa for BE in self.BEs_edge], self.BEs_edge[0].xa), 
             np.append([BE.ya for BE in self.BEs_edge], self.BEs_edge[0].ya), 
             'bo-',markersize=5,label='Boundary Elements '+str(self.Ne_edge))
        
        if (self.BEs_edge[0].element_type=="Quad"):
            plt.scatter([BE.xc for BE in self.BEs_edge], [BE.yc for BE in self.BEs_edge], color='b', s=25)
        
        #Trace elements
        if (self.TraceOn):
            for i in range(self.Num_trace):
                plt.plot([self.BEs_trace[i][0].xc, self.BEs_trace[i][0].xc],
                             [self.BEs_trace[i][0].yc,self.BEs_trace[i][0].yc],
                             'go-',  markersize=5, label='Trace Elements '+str(self.Ne_trace))
                plt.plot([self.BEs_trace[i][0].xa, self.BEs_trace[i][0].xb],
                             [self.BEs_trace[i][0].ya,self.BEs_trace[i][0].yb],
                             'go-',  markersize=2)
                for j in range(self.NumE_t[i]-1):
                            plt.plot([self.BEs_trace[i][j].xa,self.BEs_trace[i][j+1].xb],
                                     [self.BEs_trace[i][j].ya,self.BEs_trace[i][j+1].yb], 
                                     'go-', markersize=2)
                            plt.plot([self.BEs_trace[i][j].xc,self.BEs_trace[i][j+1].xc],
                                     [self.BEs_trace[i][j].yc,self.BEs_trace[i][j+1].yc], 
                                     'go-', markersize=5)
        
        if (Annotation):
            #Show marker index-convenient for BC assignment
            for i in range(self.Num_boundary):
                Node=self.Pts_e[i]
                if (i==self.Num_boundary-1): Node_next=self.Pts_e[0] #round connect
                else: Node_next=self.Pts_e[i+1]
                
                rightmiddle=line_leftright(Node,Node_next,space*0.5)[1]
                plt.text(*rightmiddle.T,"%s"%(i),fontsize=10)
            
            for i in range(self.Num_trace):
                Node,Node_next=self.Pts_t[i][0],self.Pts_t[i][1]
                
                rightmiddle=line_leftright(Node,Node_next,space*0.3)[1]
                plt.text(*rightmiddle.T,"%s"%(i+self.Num_boundary),fontsize=10)

        
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.title('BEM Mesh')
        plt.xlabel('x(m)')
        plt.ylabel('y(m)')
        plt.show()

    def plot_Solution(self,v_range=(0,50),p_range=(50,100),resolution=50):
        """Plot pressure&velocity field and Preview the streamline

        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """

        debug=0
        
        #Calculate pressure and velocity field
        from matplotlib import path
        Polygon = path.Path(self.Pts_e)
        
        N = resolution        # number of points in the x and y directions
        
        xmin,ymin=self.domain_min[0],self.domain_min[1]
        xmax,ymax=self.domain_max[0],self.domain_max[1]
        space=0.0000001*calcDist((xmin,ymin),(xmax,ymax))
        
        xi,yi=np.linspace(xmin-space, xmax+space, N),np.linspace(ymin-space, ymax+space, N)
        X, Y = np.meshgrid(xi,yi)  # generates a mesh grid
        #Calculate the velocity and pressure field
        p = np.empty((N, N), dtype=float)
        u = np.empty((N, N), dtype=float)
        v = np.empty((N, N), dtype=float)
        
        for i in range(N):
            for j in range(N):
                Pts=(X[i,j], Y[i,j])
                flag=Polygon.contains_points([Pts])
                #print(Pts,flag)
                #flag=True
                if (flag==True):
                    puv=self.get_Solution(Pts)
                    p[i,j],u[i,j],v[i,j]=puv[0],puv[1],puv[2]
                else:#point is not within the domain
                    p[i,j]=u[i,j]=v[i,j]= "nan"
            
        
        fig, axes = plt.subplots(ncols=3,figsize=(15, 15))
        Vtotal= np.sqrt(u**2+v**2)
        
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        
        for i, ax in enumerate(axes.flat):
            ax.set(xlim=[xmin-space, xmax+space],ylim=[ymin-space, ymax+space],aspect='equal')

            #Background Mesh
            ax.plot(np.append([BE.xa for BE in self.BEs_edge], self.BEs_edge[0].xa), 
                         np.append([BE.ya for BE in self.BEs_edge], self.BEs_edge[0].ya), 
                         'k-')
            for ti in range(self.Num_trace):
                ax.plot(np.append([BE.xb for BE in self.BEs_trace[ti]], self.BEs_trace[ti][0].xa),
                        np.append([BE.yb for BE in self.BEs_trace[ti]], self.BEs_trace[ti][0].ya),
                        'k-')
        

            if i==0:
                ax.set_title(r'Velocity Field')
                level = np.linspace(v_range[0], v_range[1], 15, endpoint=True)
                #im=ax.contour(X, Y, Vtotal,level,linewidths=1.2)
                im=ax.contourf(X, Y, Vtotal,level)
                divider = make_axes_locatable(ax)
                cax1=divider.append_axes("right", "10%", pad=0.15)
                cbar1 = plt.colorbar(im, cax=cax1,format="%.2f")
            if i==1:
                ax.set_title(r'Pressure Field')
                #im=ax.pcolormesh(X,Y,Vtotal,vmax=Vtotal_max)
                extent=(xmin,xmax,ymin,ymax)
                #im=ax.imshow(p,vmin=p_range[0],vmax=p_range[1],extent=extent,origin='lower',interpolation='nearest',cmap=plt.cm.jet)
                im=ax.imshow(p,vmin=p_range[0],vmax=p_range[1],extent=extent,origin='lower',interpolation='bicubic',cmap=plt.cm.jet)
                divider = make_axes_locatable(ax)
                cax2=divider.append_axes("right", "10%", pad=0.15)
                cbar2 = plt.colorbar(im, cax=cax2,format="%.2f")
            if i==2:
                import matplotlib.colors as colors
                import warnings
                warnings.filterwarnings('ignore') #hide the warnning when "nan" involves
                ax.set_title(r'Streamline')
                level=colors.Normalize(vmin=v_range[0],vmax=v_range[1])
                strm=ax.streamplot(X, Y, u, v,color=Vtotal,norm=level)
                im=strm.lines
                divider = make_axes_locatable(ax)
                cax3=divider.append_axes("right", "10%", pad=0.15)
                cbar3 = plt.colorbar(im, cax=cax3,format="%.2f")

        
        fig.tight_layout()
        plt.savefig('Field_Plot.png',dpi=300)
        plt.show()      
        
        return p,u,v
        
    def plot_SolutionBD(self):
        """Line plot solution along the boundary
        
        Author:Bin Wang(binwang.0213@gmail.com)
        Date: July. 2017
        """
        Pts=EndPointOnPolygon(self.Pts_e,Nseg=10*len(self.Pts_e))
        Y=np.array([self.get_Solution(p) for p in Pts])
        
        X=[i for i in range(len(Y))]
        
        self.plot_PUV_Pts(X, Y)
        return Y

    def plot_Solution_overline(self,Pts0,Pts1):
        Pts = EndPointOnLine(Pts0, Pts1, Nseg=100, refinement="linspace")
        Y = np.array([self.get_Solution(p) for p in Pts])
        X = [calcDist(Pts[0],Pts1) for Pts1 in Pts]

        self.plot_PUV_Pts(X,Y)
        return X,Y

    ###########Additional Tools###############
    def plot_PUV_Pts(self,X,Y):
        #General line plot for PUV see plot_Solution_overline
        p = Y[:, 0]
        u = Y[:, 1]
        v = Y[:, 2]

        fig, axes = plt.subplots(nrows=3, figsize=(7, 7))
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        for i, ax in enumerate(axes.flat):
            if i == 0:
                ax.set_title(r'Pressure along Boundary')
                im = ax.plot(X, p)
                divider = make_axes_locatable(ax)
            if i == 1:
                ax.set_title(r'Velocity(x) along boundary')
                im = ax.plot(X, u)
                divider = make_axes_locatable(ax)
            if i == 2:
                ax.set_title(r'Velocity(y) along boundary')
                im = ax.plot(X, v)
                divider = make_axes_locatable(ax)

        fig.tight_layout()
        plt.show()

    def getNodeId(self,eleid,local_id,EdgeorTrace='Edge'):
        #DOF distribution [Edge,Trace,Well]
        #[1,2,3] [3,4,5] [5,6,7]
        #get the global node index based on the element id and local id

        global_id=0

        if(EdgeorTrace=='Edge'):  # Edge
            #Special Case of Round end connect for linear and quad element
            if(eleid == self.Ne_edge - 1 and local_id == self.Nedof_edge-1 and self.Nedof_edge>1): #This is the last node at the last element
                global_id = 0
                return global_id
        
            if (self.TypeE_edge == "Quad"):
                global_id=2*eleid+local_id
            elif (self.TypeE_edge == "Linear"):
                global_id = eleid + local_id
            else:
                global_id = eleid

        if(self.Nedof_edge>1):#Linear and Quad element
            start_id=(self.Nedof_edge-1)*self.Ne_edge
        else:#Const element
            start_id = self.Ne_edge
        if(EdgeorTrace == 'Trace'):  # Trace
            if (self.TypeE_trace == "Quad"):
                global_id = start_id + 2 * eleid + local_id
            elif (self.TypeE_trace == "Linear"):
                global_id = start_id + eleid + local_id
            else:
                global_id = start_id + eleid
            
        

        return global_id

    def point_on_element(self,Pts):
        #check and determine the element which a point is located on edge or trace
        #Currently, only boundary edge support
        #[Output] [elementID1,elementID2....] -1 - not on edge
        
        element=[]
        for i in range(self.Num_boundary):#edge search
            Node=self.Pts_e[i]
            if (i==self.Num_boundary-1): 
                Node_next=self.Pts_e[0] #round connect
            else: 
                Node_next=self.Pts_e[i+1]
            
            if (point_on_line(Pts,Node,Node_next)):# Found! point on a edge
                elementID=self.bdmarker2element(i)#element index on this edge
                for j in range(len(elementID)):
                    Pts_a=(self.BEs_edge[elementID[j]].xa,self.BEs_edge[elementID[j]].ya)
                    Pts_b=(self.BEs_edge[elementID[j]].xb,self.BEs_edge[elementID[j]].yb)
                    if(point_on_line(Pts,Pts_a,Pts_b)):
                        element.append(elementID[j])
                        break #element belonging is enough
        
        if(len(element)>=1): #1 general element 2 edge connection points
            return element
        else: 
            return -1

    def element2edge(self,idx_element):
        #find the edge index form a elemetn index
        #Currently only support for edge element

        pts_c=[self.BEs_edge[idx_element].xc,self.BEs_edge[idx_element].yc] #central point of this element

        for i in range(self.Num_boundary):#edge search
            Node=self.Pts_e[i]
            if (i==self.Num_boundary-1): 
                Node_next=self.Pts_e[0] #round connect
            else: 
                Node_next=self.Pts_e[i+1]
            if (point_on_line(pts_c,Node,Node_next)):#edge found
                return i

        print('Error!! Func-element2edge')   

    def bdmarker2element(self,markerID):
        #find the element index based on bd markerID(boundary index)
        # example： markerID=3  Element index=[0 1]

        index=[]
        if (markerID>self.Num_boundary-1):#this is a trace
            tracerID=markerID-self.Num_boundary
            for i in range(len(self.BEs_trace[tracerID])):
                index.append([tracerID,i])
        
        else:#this is a boundary edge
            elementID_start=0
            for i in range(markerID):
                elementID_start+=self.NumE_bd[i]
            for i in range(self.NumE_bd[markerID]):
                index.append(elementID_start+i)
        
        return np.array(index)

    def bd2element(self,element_type="Const",eleid=0,node_values=[]):
        #extract the node_values of a element from a sets of values along a edge
        #eleid is the local index, e.g 3 element on a edge, eleid=0,1,2

        if(element_type=="Const"):#[0] [1]
            return [node_values[eleid]]
        elif(element_type=="Linear"):#[0,1] [1,2]
            return [node_values[eleid],node_values[eleid+1]]
        elif(element_type=="Quad"):#[0,1,2] [2,3,4]
            return [node_values[eleid*2],node_values[eleid*2+1],node_values[eleid*2+2]]

    def EndPoint2bdmarker(self,Pts0,Pts1):
        #find the bd_markerid based on two end points[Pts0,Pts1]
        #currently only boundary edge are support

        pts_c=[(Pts0[0]+Pts1[0])*0.5,(Pts0[1]+Pts1[1])*0.5] #central point of this element

        for i in range(self.Num_boundary):#edge search
            Node=self.Pts_e[i]
            if (i==self.Num_boundary-1): 
                Node_next=self.Pts_e[0] #round connect
            else: 
                Node_next=self.Pts_e[i+1]
            if (point_on_line(pts_c,Node,Node_next)):#edge found
                return i
        print("Can not find the bd_markerID",Pts0,Pts1)
    
