module lay_parameters
  !     Module to define the constant patrameters:
  !     maxlay: The maximum number of layers to be simulated
  !     map:    The maximum number of parameters, which depends on the layer number
  !     ndatap: Number of datapoints for the arrays
  !     max_hr: ?
  !     pdq:    ?
  parameter(maxlay=400,map=7*maxlay+12,ndatap=1000,max_hr=5000,np_conv=500,pdq=0.02d0)
  !     To get ideas of speed measure the runtime and times inside of some functions
  real*4       total_time(2), tmp_time
   
  save
end

program fit_pnr_mult
  !    Fit of the polarized neutron reflectivity with polarization analyzis
  !    Data from TREFF
  !    Super-Parratt formalism
  !    Written by Emmanuel Kentzinger with changes from Artur Glavic
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 lamda
  complex*16 ci
  real*8 x(ndatap),y(ndatap),sig(ndatap)
  real*8 a(map)
  integer*4 lista(map)
  real*8 covar(map,map),alpha(map,map)
  integer*4 pp(ndatap),m_pp(ndatap),mm(ndatap),m_mm(ndatap),pm(ndatap),m_pm(ndatap),mp(ndatap),m_mp(ndatap)
  character*128 fpp,fmm,fpm,fmp
  character*128 ent_file, max_iter_string
  integer*4     maximum_iterations
  logical :: file_exists
  common/pici/pi,ci
  common/wave/lamda,dlamda
  common/nlayer/nlay
  common/reso/s1,s2,sl,d1,d2
  common/pos/qq,sigmaq
  common/cons1/mfree,icons,itype_of_cons(map),i_para_ref(map)
  common/cons2/n_para_eq_iref(map),nr_para_eq_iref(map,map),i_para_sum(map)
  common/thicknesses/d(maxlay)
  common/pol/poli(3),polf(3)
  common/lamdafirst/alamda_first
  common/chi0/ochisq0
  common/data/ndata_pp,ndata_mm,ndata_pm,ndata_mp
  common/entryfiles/fpp,fmm,fpm,fmp
  common/layers/ntop,nincell,ncell,nbelow

  tmp_time=dtime(total_time)
  
  !! Read the .ent file name from command line
  call getarg(1,ent_file)
  INQUIRE(FILE=ent_file, EXIST=file_exists)
  if (file_exists) then
  else
    write(*,*) "File ", ent_file, " does not exist."
    go to 9999
  endif
  !! Read maximum iterations from command line
  call getarg(2,max_iter_string)
  if(max_iter_string.eq.'') then
      maximum_iterations=50
  else
      read(max_iter_string,*) maximum_iterations
  endif
  
  pi=dacos(-1.d0)
  ci=dcmplx(0.d0,1.d0)

  poli(1)=0.d0
  poli(3)=0.d0
  polf(1)=0.d0
  polf(3)=0.d0

  open(5,file=ent_file)
  open(8,file='result')

  read(5,*) s1
  read(5,*) s2
  read(5,*) sl
  read(5,*) d1
  read(5,*) d2
  read(5,*)
  write(8,*) 'first slit opening (mm)',s1
  write(8,*) 'second slit opening (mm)',s2
  write(8,*) 'sample length (mm)',sl
  write(8,*) 'distance from first slit to sample',d1
  write(8,*) 'distance from second slit to sample',d2
  write(8,*)

  read(5,'(a)') fpp
  read(5,*) ndata_pp
  read(5,'(a)') fmm
  read(5,*) ndata_mm
  read(5,'(a)') fpm
  read(5,*) ndata_pm
  read(5,'(a)') fmp
  read(5,*) ndata_mp
  read(5,*)
  len = index(fpp,' ')-1
  write(8,*) 'entry file for ++ reflectivity: ',fpp(1:len)
  write(8,*) 'number of theta values ++ =',ndata_pp
  len = index(fmm,' ')-1
  write(8,*) 'entry file for -- reflectivity: ',fmm(1:len)
  write(8,*) 'number of theta values -- =',ndata_mm
  len = index(fpm,' ')-1
  write(8,*) 'entry file for +- reflectivity: ',fpm(1:len)
  write(8,*) 'number of theta values +- =',ndata_pm
  len = index(fmp,' ')-1
  write(8,*) 'entry file for -+ reflectivity: ',fmp(1:len)
  write(8,*) 'number of theta values -+ =',ndata_mp
  write(8,*)

  call read_data(x,y,sig,ndata)
  write(8,*) 'number of data =',ndata
  if (ndata.gt.ndatap) then
    stop 'ndata > ndatap'
  endif

  read(5,*) lamda
  read(5,*) dlamda
  read(5,*)
  write(8,*) 'wavelength=',lamda
  write(8,*) 'wavelength width (rms)=',dlamda
  write(8,*)

  ma=0

  read(5,*) ntop
  read(5,*)
  do i=1,ntop
    do j=1,7
      read(5,*) a(ma+j)
    enddo
    read(5,*)
    ma=ma+7
  enddo
  read(5,*) nincell
  read(5,*)
  do i=1,nincell
    do j=1,7
      read(5,*) a(ma+j)
    enddo
    read(5,*)
    ma=ma+7
  enddo
  read(5,*) ncell
  read(5,*)
  read(5,*) nbelow
  read(5,*)
  do i=1,nbelow
    do j=1,7
      read(5,*) a(ma+j)
    enddo
    read(5,*)
    ma=ma+7
  enddo
  do j=1,6
    read(5,*) a(ma+j)
  enddo
  read(5,*)
  ma=ma+6
  do j=1,2
    read(5,*) a(ma+j)
  enddo
  read(5,*)
  ma=ma+2
  do j=1,4
    read(5,*) a(ma+j)
  enddo
  read(5,*)
  ma=ma+4

  nlay=ntop+nincell*ncell+nbelow
  write(8,*) 'total number of layers :',nlay
  if (nlay.gt.maxlay) then
    stop 'nlay > maxlay'
  endif

  write(8,*) 'total number of parameters :',ma
  if (ma.gt.map) then
    stop 'ma > map'
  endif

  write(8,*) 'initial parameters :'
  np=0
  do i=1,ntop
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do i=1,nincell
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do i=1,nbelow
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do j=1,6
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)
  do j=1,2
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)
  do j=1,4
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)

  read(5,*) ifit
  write(8,*) 'ifit=',ifit
  read(5,*)
  write(8,*)
  if (ifit.eq.0) then
    close(5)
    call param(a)
    call make_sim(x,ndata)
    call calchi(x,y,sig,ndata,chisq,valfitsq)
    write(8,*) 'valfit=',dsqrt(valfitsq/dfloat(ndata))
    write(8,*) 'chi=',dsqrt(chisq/dfloat(ndata))
    write(8,*)       
    goto 77
  endif
  read(5,*) mfree
  write(8,*) 'number of degrees of freedom :',mfree
  write(8,*) 'indices of fitted parameters :'
  read(5,*) (lista(i),i=1,mfree)
  write(8,*)(lista(i),i=1,mfree)
  read(5,*)
  write(8,*)
  read(5,*) icons
  write(8,*) 'number of constraint equalities :',icons
  mfit=mfree
  do j=1,icons
    read(5,*) itype_of_cons(j)
    write(8,*) 'constraint number:',j
    if (itype_of_cons(j).eq.1) then
      write(8,*) 'constraint of the type b=c=...=a'
      read(5,*) i_para_ref(j)
      write(8,*) 'parameter a with repect to which the constraint equality has to be set',i_para_ref(j)
      read(5,*) n_para_eq_iref(j)
      write(8,*) 'number of para that have to be kept equal to this para',n_para_eq_iref(j)
      read(5,*) (nr_para_eq_iref(j,k),k=1,n_para_eq_iref(j))
      write(8,*) 'list of those parameters',(nr_para_eq_iref(j,k),k=1,n_para_eq_iref(j))
      do k=1,n_para_eq_iref(j)
        lista(mfit+k)=nr_para_eq_iref(j,k)
        a(nr_para_eq_iref(j,k))=a(i_para_ref(j))
      enddo
      mfit=mfit+n_para_eq_iref(j)
    endif
    if (itype_of_cons(j).eq.2) then
      write(8,*) 'constraint of the type b+a=cste'
      read(5,*) i_para_ref(j)
      write(8,*) 'parameter a',i_para_ref(j)
      read(5,*) i_para_sum(j)
      write(8,*) 'parameter b',i_para_sum(j)
      lista(mfit+1)=i_para_sum(j)
      mfit=mfit+1
    endif
    if (itype_of_cons(j).ne.1.and.itype_of_cons(j).ne.2) stop 'unknown constraint type'
  enddo
  write(8,*)
  write(8,*) 'total number of fitted parameters=',mfit 
  read(5,*)
  read(5,*) alamda_first
  read(5,*) ntest
  write(8,*)
  write(8,*) 'alamda_first=',alamda_first
  write(8,*) 'ntest=',ntest
  write(8,*)
  write(8,*)
  close(5)

  ichi_improve=0
  alamda=-1.d0
  iter=1
  do i=1,10
    write(8,*) '############################################################'
  enddo
  write(8,*)
  write(8,*)
  write(8,*) 'iter=',iter,' alamda=',alamda
  write(8,*)
  call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
  write(8,*) 'kept parameters :'
  np=0
  do i=1,ntop
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do i=1,nincell
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do i=1,nbelow
    do j=1,7
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
  enddo
  do j=1,6
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)
  do j=1,2
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)
  do j=1,4
    np=np+1
    write(8,*) np,' ',a(np)
  enddo
  write(8,*)
  if (chisq.lt.ochisq0) then
    !open(9,file='simulation')
    call param(a)
    call make_sim(x,ndata)
    write(8,*) ' chi2 has been improved by', (ochisq0-chisq)/ochisq0*100.d0, ' %'
    ichi_improve=ichi_improve+1
    write(8,*) 'number of chi-improvements=',ichi_improve
  else
    write(8,*) ' chi2 has not been improved'
    write(8,*) 'number of chi-improvements=',ichi_improve
  endif
  chi=dsqrt(chisq/dfloat(ndata-mfree))
  write(8,*) ' chi=',chi
  write(8,*)
  write(8,*)
  itest=0
  
  open(82,file='status')
  write(82,*) 'iteration: ',iter,' - chi: ',chi
  close(82)
  
  do 10 iter=2,maximum_iterations
    open(82,file='status')
    write(82,*) 'iteration: ',iter,' - chi: ',chi
    close(82)
    do i=1,10
      write(8,*) '############################################################'
    enddo
    write(8,*)
    write(8,*)
    write(8,*) 'iter=',iter,' itest=',itest,' alamda=',alamda
    write(8,*)
    chisq0=chisq
    call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
    write(8,*)
    write(8,*) 'kept parameters :'
    np=0
    do i=1,ntop
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np)
      enddo
      write(8,*)
    enddo
    do i=1,nincell
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np)
      enddo
      write(8,*)
    enddo
    do i=1,nbelow
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np)
      enddo
      write(8,*)
    enddo
    do j=1,6
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
    do j=1,2
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
    do j=1,4
      np=np+1
      write(8,*) np,' ',a(np)
    enddo
    write(8,*)
    if(chisq.lt.chisq0) then
      !open(9,file='simulation')
      call param(a)
      call make_sim(x,ndata)
      write(8,*) ' chi2 has been improved by', (chisq0-chisq)/chisq0*100.d0, ' %'
      ichi_improve=ichi_improve+1
      write(8,*) 'number of chi-improvements=',ichi_improve
    else
      write(8,*) ' chi2 has not been improved'
      write(8,*) 'number of chi-improvements=',ichi_improve
    endif
    chi=dsqrt(chisq/dfloat(ndata-mfree))
    write(8,*) ' chi=',chi
    write(8,*)
    write(8,*)
    dchisq=dabs(chisq-chisq0)/chisq0
    if (chisq.ge.chisq0) then
      itest=0
    else if (dchisq.lt.1.0d-2) then
      itest=itest+1
    endif
    if (itest.eq.ntest) goto 88
  10   continue
  88   if (iter.le.maximum_iterations) then
    alamda=0.d0
    write(8,*) 'itest=',itest,' alamda=',alamda
    call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
    write(8,*) 'list of parameters:'
    do i=1,ma
      write(8,100) i,a(i),' +/- ',dsqrt(covar(i,i))
    enddo
    write(8,*) 'chi2= ',chisq
    chi=dsqrt(chisq/dfloat(ndata-mfree))
    write(8,*) 'normalized chi= ',chi
    write(8,*) 'fit obtained in ', iter,' iterations'
    write(8,*) 'list of parameters with uncertaincies multiplied by morm. chi :'
    np=0
    do i=1,ntop
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
      enddo
      write(8,*)
    enddo
    do i=1,nincell
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
      enddo
      write(8,*)
    enddo
    do i=1,nbelow
      do j=1,7
        np=np+1
        write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
      enddo
      write(8,*)
    enddo
    do j=1,6
      np=np+1
      write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
    enddo
    write(8,*)
    do j=1,2
      np=np+1
      write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
    enddo
    write(8,*)
    do j=1,4
      np=np+1
      write(8,*) np,' ',a(np),' +/- ',dsqrt(covar(np,np))*chi
    enddo
    write(8,*)
  else
    write(8,*) 'not enough iterations, iter=',iter
  endif
  100  format(10x,i3,x,f15.5,a5,f13.5)
  write(8,*)
  write(8,*) 'results generated with program "fit_pnr_mult_newcons.f90"'   
  77 close(8)
  write(*,*) dtime(total_time)
9999 end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
