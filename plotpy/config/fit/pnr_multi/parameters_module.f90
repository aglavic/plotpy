module lay_parameters
  !     Module to define the constant patrameters:
  !     maxlay: The maximum number of layers to be simulated
  !     map:    The maximum number of parameters, which depends on the layer number
  !     ndatap: Number of datapoints for the arrays
  !     max_hr: ?
  !     pdq:    ?
  parameter(maxlay=400,map=7*maxlay+12,ndatap=4000,max_hr=5000,np_conv=500,pdq=0.02d0)
  !     To get ideas of speed measure the runtime and times inside of some functions
  real*4       total_time(2), tmp_time
   
  save
end
