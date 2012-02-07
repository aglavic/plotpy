subroutine calchi(x,y,sig,ndata,chisq,valfitsq)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  dimension x(ndatap),y(ndatap),sig(ndatap)
  dimension ymod(ndatap)
  complex*16 ci
  real*8 lamda
  common/pol/poli(3),polf(3)
  common/eff/pol1,pol2,fl1,fl2
  common/data/ndata_pp,ndata_mm,ndata_pm,ndata_mp
  common/qy_ht/q_hr(max_hr),ref_hr(max_hr),q_max
  common/pici/pi,ci
  common/wave/lamda,dlamda

  !      ++
  poli(2)=pol1*fl1
  polf(2)=pol2
  q_max=4.d0*pi/lamda*dsin(x(ndata_pp))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=1,ndata_pp
    ymod(i)=refconv(x(i))
  enddo
  nn=ndata_pp

  !      --
  poli(2)=-pol1
  polf(2)=-pol2*fl2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mm))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=nn+1,nn+ndata_mm
    ymod(i)=refconv(x(i))
  enddo
  nn=nn+ndata_mm

  !      +-
  poli(2)=pol1*fl1
  polf(2)=-pol2*fl2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_pm))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=nn+1,nn+ndata_pm
    ymod(i)=refconv(x(i))
  enddo
  nn=nn+ndata_pm

  !      -+
  poli(2)=-pol1
  polf(2)=pol2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mp))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=nn+1,nn+ndata_mp
    ymod(i)=refconv(x(i))
  enddo

  write(8,*) 'ymod s calculated in calchi'
  chisq=0.d0
  valfitsq=0.d0
  do 14 i=1,ndata
    sig2i=1.d0/(sig(i)*sig(i))
    dy=y(i)-ymod(i)
    if (ymod(i).eq.0.d0) ymod(i)=1.d-10
    dlogy=(dlog(y(i))-dlog(ymod(i)))/dlog(10.d0)
    chisq=chisq+dy*dy*sig2i
    valfitsq=valfitsq+dlogy*dlogy
  14 enddo
  write(8,*) 'end of calchi'
  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
