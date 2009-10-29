subroutine param(a)
  implicit real*8 (a-h,o-z)
  parameter(maxlay=250,map=7*maxlay+12)
  real*8 a(map)
  real*8 d(maxlay),nbr(maxlay+1),nbi(maxlay+1),np(maxlay+1)
  real*8 theta(maxlay+1),phi(maxlay+1)
  real*8 bx(maxlay+1),by(maxlay+1),bz(maxlay+1)
  complex*16 ci
  common/pici/pi,ci
  common/thicknesses/d
  common/sample/nbr,nbi,np
  common/rough/sigma(maxlay+1)
  common/fields/bx,by,bz
  common/nlayer/nlay
  common/eff/pol1,pol2,fl1,fl2
  common/calbg/cal,bg
  common/layers/ntop,nincell,ncell,nbelow

  ma=0
  do m=1,ntop
    d(m)=dabs(a(ma+1))
    nbr(m)=dabs(a(ma+2))*1.d-6
    nbi(m)=a(ma+3)*1.d-6
    np(m)=a(ma+4)*1.d-6
    theta(m)=a(ma+5)*pi/180.d0
    phi(m)=a(ma+6)*pi/180.d0
    sigma(m)=dabs(a(ma+7))
    ma=ma+7
  enddo

  do m=ntop+1,ntop+nincell
    d(m)=dabs(a(ma+1))
    nbr(m)=dabs(a(ma+2))*1.d-6
    nbi(m)=a(ma+3)*1.d-6
    np(m)=a(ma+4)*1.d-6
    theta(m)=a(ma+5)*pi/180.d0
    phi(m)=a(ma+6)*pi/180.d0
    sigma(m)=dabs(a(ma+7))
    ma=ma+7
  enddo
  ma=ma-7*nincell
  do j=1,ncell-1
    do jj=1,nincell
      m=ntop+j*nincell+jj
      d(m)=dabs(a(ma+1))
      nbr(m)=dabs(a(ma+2))*1.d-6
      nbi(m)=a(ma+3)*1.d-6
      np(m)=a(ma+4)*1.d-6
      theta(m)=a(ma+5)*pi/180.d0
      phi(m)=a(ma+6)*pi/180.d0
      sigma(m)=dabs(a(ma+7))
      ma=ma+7 
    enddo
    ma=ma-7*nincell
  enddo
  ma=ma+7*nincell

  do m=ntop+ncell*nincell+1,ntop+ncell*nincell+nbelow
    d(m)=dabs(a(ma+1))
    nbr(m)=dabs(a(ma+2))*1.d-6
    nbi(m)=a(ma+3)*1.d-6
    np(m)=a(ma+4)*1.d-6
    theta(m)=a(ma+5)*pi/180.d0
    phi(m)=a(ma+6)*pi/180.d0
    sigma(m)=dabs(a(ma+7))
    ma=ma+7
  enddo

  m=nlay+1
  nbr(m)=a(ma+1)*1.d-6
  nbi(m)=dabs(a(ma+2))*1.d-6
  np(m)=a(ma+3)*1.d-6
  theta(m)=a(ma+4)*pi/180.d0
  phi(m)=a(ma+5)*pi/180.d0
  sigma(m)=dabs(a(ma+6))
  ma=ma+6

  do m=1,nlay+1
    bx(m)=dcos(phi(m))*dsin(theta(m))
    by(m)=dsin(phi(m))*dsin(theta(m))
    bz(m)=dcos(theta(m))
  enddo

  cal=dabs(a(ma+1))
  bg=dabs(a(ma+2))*1.d-6
  ma=ma+2

  pol1=dabs(a(ma+1))
  pol2=dabs(a(ma+2))
  fl1=dabs(a(ma+3))
  fl2=dabs(a(ma+4))

  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
