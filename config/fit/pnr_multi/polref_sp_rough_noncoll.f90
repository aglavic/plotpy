!    Taking into account the roughness in a proper way.
!    Also valid in the case of non-collinear magnetizations.
!    For the computation of the damping factor associated to roughness, 
!    we redefine the pm's as functions of sigma.bm_rough, where bm_rough is
!    along the vector of incident polarization poli, with a sign given by
!    the scalar product poli*bm.
function polref_sp_rough(q)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  complex*16 ci
  real*8 d(maxlay),nbr(maxlay+1),nbi(maxlay+1),np(maxlay+1)
  real*8 bx(maxlay+1),by(maxlay+1),bz(maxlay+1)
  real*8 sc_pr(maxlay+1),bx_rough(0:maxlay+1),by_rough(0:maxlay+1),bz_rough(0:maxlay+1)
  complex*16 p(2,2,0:maxlay+1),inv_p(2,2,0:maxlay+1),ei_phi(2,2,0:maxlay)
  complex*16 pnucl2,ei_phi_plus,ei_phi_minus
  complex*16 x(2,2,0:maxlay+1),r(2,2)
  complex*16 p_plus,p_minus
  complex*16 p_rough_plus(0:maxlay+1),p_rough_minus(0:maxlay+1)
  complex*16 damp_plus,damp_minus
  complex*16 damp(2,2,0:maxlay)
  common/pici/pi,ci
  common/nlayer/nlay
  common/thicknesses/d
  common/sample/nbr,nbi,np
  common/fields/bx,by,bz
  common/fields_rough/sc_pr,bx_rough,by_rough,bz_rough
  common/calx/p,inv_p,ei_phi
  common/rough/sigma(maxlay+1)
  common/damp_rough/damp

  p0=q/2.d0
  p(1,1,0)=dcmplx(p0,0.d0)
  p(2,2,0)=dcmplx(p0,0.d0)
  p(1,2,0)=dcmplx(0.d0,0.d0)
  p(2,1,0)=dcmplx(0.d0,0.d0)
  inv_p(1,1,0)=dcmplx(1.d0/p0,0.d0)
  inv_p(2,2,0)=dcmplx(1.d0/p0,0.d0)
  inv_p(1,2,0)=dcmplx(0.d0,0.d0)
  inv_p(2,1,0)=dcmplx(0.d0,0.d0)
  ei_phi(1,1,0)=dcmplx(1.d0,0.d0)
  ei_phi(2,2,0)=dcmplx(1.d0,0.d0)
  ei_phi(1,2,0)=dcmplx(0.d0,0.d0)
  ei_phi(2,1,0)=dcmplx(0.d0,0.d0)
  p_rough_plus(0)=p0
  p_rough_minus(0)=p0
  p02=p0*p0
  do m=1,nlay
    pnucl2=4.d0*pi*dcmplx(nbr(m),-nbi(m))
    pmag2=4.d0*pi*np(m)
    p_plus=cdsqrt(p02-pnucl2-pmag2)
    p_minus=cdsqrt(p02-pnucl2+pmag2)
    p(1,1,m)=0.5d0*((1.d0+bz(m))*p_plus+(1.d0-bz(m))*p_minus)
    p(2,2,m)=0.5d0*((1.d0-bz(m))*p_plus+(1.d0+bz(m))*p_minus)
    p(1,2,m)=0.5d0*(bx(m)-ci*by(m))*(p_plus-p_minus)
    p(2,1,m)=0.5d0*(bx(m)+ci*by(m))*(p_plus-p_minus)
    inv_p(1,1,m)=0.5d0*((1.d0+bz(m))/p_plus+(1.d0-bz(m))/p_minus)
    inv_p(2,2,m)=0.5d0*((1.d0-bz(m))/p_plus+(1.d0+bz(m))/p_minus)
    inv_p(1,2,m)=0.5d0*(bx(m)-ci*by(m))*(1.d0/p_plus-1.d0/p_minus)
    inv_p(2,1,m)=0.5d0*(bx(m)+ci*by(m))*(1.d0/p_plus-1.d0/p_minus)
    ei_phi_plus=cdexp(ci*p_plus*d(m))
    ei_phi_minus=cdexp(ci*p_minus*d(m))
    ei_phi(1,1,m)=0.5d0*((1.d0+bz(m))*ei_phi_plus+(1.d0-bz(m))*ei_phi_minus)
    ei_phi(2,2,m)=0.5d0*((1.d0-bz(m))*ei_phi_plus+(1.d0+bz(m))*ei_phi_minus)
    ei_phi(1,2,m)=0.5d0*(bx(m)-ci*by(m))*(ei_phi_plus-ei_phi_minus)
    ei_phi(2,1,m)=0.5d0*(bx(m)+ci*by(m))*(ei_phi_plus-ei_phi_minus)
    pmag2_rough=pmag2*dabs(sc_pr(m))
    p_rough_plus(m)=cdsqrt(p02-pnucl2-pmag2_rough)
    p_rough_minus(m)=cdsqrt(p02-pnucl2+pmag2_rough)
  enddo
  m=nlay+1
  pnucl2=4.d0*pi*dcmplx(nbr(m),-nbi(m))
  pmag2=4.d0*pi*np(m)
  p_plus=cdsqrt(p02-pnucl2-pmag2)
  p_minus=cdsqrt(p02-pnucl2+pmag2)
  p(1,1,m)=0.5d0*((1.d0+bz(m))*p_plus+(1.d0-bz(m))*p_minus)
  p(2,2,m)=0.5d0*((1.d0-bz(m))*p_plus+(1.d0+bz(m))*p_minus)
  p(1,2,m)=0.5d0*(bx(m)-ci*by(m))*(p_plus-p_minus)
  p(2,1,m)=0.5d0*(bx(m)+ci*by(m))*(p_plus-p_minus)
  inv_p(1,1,m)=0.5d0*((1.d0+bz(m))/p_plus+(1.d0-bz(m))/p_minus)
  inv_p(2,2,m)=0.5d0*((1.d0-bz(m))/p_plus+(1.d0+bz(m))/p_minus)
  inv_p(1,2,m)=0.5d0*(bx(m)-ci*by(m))*(1.d0/p_plus-1.d0/p_minus)
  inv_p(2,1,m)=0.5d0*(bx(m)+ci*by(m))*(1.d0/p_plus-1.d0/p_minus)
  pmag2_rough=pmag2*dabs(sc_pr(m))
  p_rough_plus(m)=cdsqrt(p02-pnucl2-pmag2_rough)
  p_rough_minus(m)=cdsqrt(p02-pnucl2+pmag2_rough)

  !    Treating damping factor due to roughness
  m=0
  if(sigma(m+1).ne.0.d0) then
    if(sc_pr(m+1).gt.0.d0) then
      damp_plus=cdexp(-2.d0*sigma(m+1)**2*p_rough_plus(m)*p_rough_plus(m+1))
      damp_minus=cdexp(-2.d0*sigma(m+1)**2*p_rough_minus(m)*p_rough_minus(m+1))
    else
      damp_plus=cdexp(-2.d0*sigma(m+1)**2*p_rough_plus(m)*p_rough_minus(m+1))
      damp_minus=cdexp(-2.d0*sigma(m+1)**2*p_rough_minus(m)*p_rough_plus(m+1))
    endif
    damp(1,1,m)=0.5d0*((1.d0+bz_rough(m))*damp_plus+(1.d0-bz_rough(m))*damp_minus)
    damp(2,2,m)=0.5d0*((1.d0-bz_rough(m))*damp_plus+(1.d0+bz_rough(m))*damp_minus)
    damp(1,2,m)=0.5d0*(bx_rough(m)-ci*by_rough(m))*(damp_plus-damp_minus)
    damp(2,1,m)=0.5d0*(bx_rough(m)+ci*by_rough(m))*(damp_plus-damp_minus)
  else
    damp(1,1,m)=dcmplx(1.d0,0.d0)
    damp(2,2,m)=dcmplx(1.d0,0.d0)
    damp(1,2,m)=dcmplx(0.d0,0.d0)
    damp(2,1,m)=dcmplx(0.d0,0.d0)
  endif
  do m=1,nlay
    if(sigma(m+1).ne.0.d0) then
      bmbmp1=bx_rough(m)*bx_rough(m+1)+by_rough(m)*by_rough(m+1)+bz_rough(m)*bz_rough(m+1)
      if((sc_pr(m+1).eq.0.d0).or.(sc_pr(m).eq.0.d0.and.sc_pr(m+1).gt.0.d0).or.(bmbmp1.eq.1.d0)) then
        damp_plus=cdexp(-2.d0*sigma(m+1)**2*p_rough_plus(m)*p_rough_plus(m+1))
        damp_minus=cdexp(-2.d0*sigma(m+1)**2*p_rough_minus(m)*p_rough_minus(m+1))
        goto 20
      endif
      if((sc_pr(m).eq.0.d0.and.sc_pr(m+1).lt.0.d0).or.bmbmp1.eq.-1.d0) then
        damp_plus=cdexp(-2.d0*sigma(m+1)**2*p_rough_plus(m)*p_rough_minus(m+1))
        damp_minus=cdexp(-2.d0*sigma(m+1)**2*p_rough_minus(m)*p_rough_plus(m+1))
        goto 20
      endif
      stop 'Something is not under control here...'
      20         damp(1,1,m)=0.5d0*((1.d0+bz_rough(m))*damp_plus+(1.d0-bz_rough(m))*damp_minus)
      damp(2,2,m)=0.5d0*((1.d0-bz_rough(m))*damp_plus+(1.d0+bz_rough(m))*damp_minus)
      damp(1,2,m)=0.5d0*(bx_rough(m)-ci*by_rough(m))*(damp_plus-damp_minus)
      damp(2,1,m)=0.5d0*(bx_rough(m)+ci*by_rough(m))*(damp_plus-damp_minus)
    else
      damp(1,1,m)=dcmplx(1.d0,0.d0)
      damp(2,2,m)=dcmplx(1.d0,0.d0)
      damp(1,2,m)=dcmplx(0.d0,0.d0)
      damp(2,1,m)=dcmplx(0.d0,0.d0)
    endif
  enddo

  x(1,1,nlay+1)=0.d0
  x(2,2,nlay+1)=0.d0
  x(1,2,nlay+1)=0.d0
  x(2,1,nlay+1)=0.d0
  do m=nlay,0,-1
    call cal_x(m,x)
  enddo

  do i=1,2
    do j=1,2
      r(i,j)=x(i,j,0)
    enddo
  enddo

  call cal_reflectivity(r,polref_sp_rough)

  return
end
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine cal_x(m,x)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  complex*16 p(2,2,0:maxlay+1),inv_p(2,2,0:maxlay+1),ei_phi(2,2,0:maxlay)
  complex*16 x(2,2,0:maxlay+1)
  complex*16 pmp1(2,2),inv_pm(2,2),ei_phim(2,2),xmp1(2,2),xm(2,2)
  complex*16 temp(2,2),temp_p(2,2),temp_m(2,2),temp_n(2,2),temp_d(2,2),inv_temp_d(2,2)
  complex*16 delta
  logical inversible
  complex*16 damp(2,2,0:maxlay)
  complex*16 rough_damp(2,2)
  common/calx/p,inv_p,ei_phi
  common/damp_rough/damp

  do i=1,2
    do j=1,2
      pmp1(i,j)=p(i,j,m+1)
      inv_pm(i,j)=inv_p(i,j,m)
      ei_phim(i,j)=ei_phi(i,j,m)
      xmp1(i,j)=x(i,j,m+1)
      rough_damp(i,j)=damp(i,j,m)
    enddo
  enddo

  temp=matmul(inv_pm,pmp1)
  do i=1,2
    do j=1,2
      if (i.eq.j) then
        temp_p(i,j)=1.d0+temp(i,j)
        temp_m(i,j)=1.d0-temp(i,j)
      else
        temp_p(i,j)=temp(i,j)
        temp_m(i,j)=-temp(i,j)
      endif
    enddo
  enddo

  temp_m=matmul(temp_m,rough_damp)

  temp_n=matmul(temp_p,xmp1)
  temp_d=matmul(temp_m,xmp1)
  do i=1,2
    do j=1,2
      temp_n(i,j)=temp_n(i,j)+temp_m(i,j)
      temp_d(i,j)=temp_d(i,j)+temp_p(i,j)
    enddo
  enddo

  call inv_mat(temp_d,inv_temp_d,delta,inversible)
  if (inversible) then
    continue
  else
    stop 'temp_d not inversible in cal_x'
  endif

  xm=matmul(temp_n,inv_temp_d)

  xm=matmul(matmul(ei_phim,xm),ei_phim)

  do i=1,2
    do j=1,2
      x(i,j,m)=xm(i,j)
    enddo
  enddo

  return
end
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine cal_reflectivity(r,polref)
  implicit real*8 (a-h,o-z)
  complex*16 r(2,2),rhof(2,2),rhoi(2,2),transr(2,2),temp(2,2)
  complex*16 ci,polr
  common/pici/pi,ci
  common/pol/poli(3),polf(3)

  rhoi(1,1)=0.5d0*(1.d0+poli(3))
  rhoi(2,2)=0.5d0*(1.d0-poli(3))
  rhoi(1,2)=0.5d0*(poli(1)-ci*poli(2))
  rhoi(2,1)=0.5d0*(poli(1)+ci*poli(2))

  rhof(1,1)=0.5d0*(1.d0+polf(3))
  rhof(2,2)=0.5d0*(1.d0-polf(3))
  rhof(1,2)=0.5d0*(polf(1)-ci*polf(2))
  rhof(2,1)=0.5d0*(polf(1)+ci*polf(2))

  do 1 i=1,2
    do 2 j=1,2
      transr(i,j)=dconjg(r(j,i))
    2    continue
  1 continue

  temp=matmul(rhof,matmul(r,matmul(rhoi,transr)))

  polr=temp(1,1)+temp(2,2)
  polref=dreal(polr)

  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine inv_mat(a,aminus1,delta,inversible)
  complex*16 a(2,2), aminus1(2,2),delta
  logical inversible
  delta=a(1,1)*a(2,2)-a(1,2)*a(2,1)
  if (cdabs(delta).eq.0.d0) then
    inversible=.false.
  else
    inversible=.true.
    aminus1(1,1)=a(2,2)/delta
    aminus1(1,2)=-a(1,2)/delta
    aminus1(2,1)=-a(2,1)/delta
    aminus1(2,2)=a(1,1)/delta
  endif
  return
end subroutine inv_mat
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
