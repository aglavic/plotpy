subroutine read_data(x,y,sig,ndata)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 x(ndatap),y(ndatap),sig(ndatap)
  character*128 fpp,fmm,fpm,fmp
  complex*16 ci
  common/data/ndata_pp,ndata_mm,ndata_pm,ndata_mp
  common/pici/pi,ci
  common/entryfiles/fpp,fmm,fpm,fmp

  open(9,file='pnr.dat')

  len = index(fpp,' ')-1
  open(7,file=fpp(1:len))
  do i=1,ndata_pp
    read(7,*) x(i),y(i),sig(i)
    x(i)=x(i)/1000.d0
    write(9,*) x(i)*1000.d0,y(i),sig(i)
  enddo
  close(7)
  write(9,100) '&'
  100  format(a1)
  ndata=ndata_pp

  len = index(fmm,' ')-1
  open(7,file=fmm(1:len))
  do i=ndata+1,ndata+ndata_mm
    read(7,*) x(i),y(i),sig(i)
    x(i)=x(i)/1000.d0
    write(9,*) x(i)*1000.d0,y(i),sig(i)
  enddo
  close(7)
  write(9,100) '&'
  ndata=ndata+ndata_mm

  len = index(fpm,' ')-1
  open(7,file=fpm(1:len))
  do i=ndata+1,ndata+ndata_pm
    read(7,*) x(i),y(i),sig(i)
    x(i)=x(i)/1000.d0
    write(9,*) x(i)*1000.d0,y(i),sig(i)
  enddo
  close(7)
  write(9,100) '&'
  ndata=ndata+ndata_pm

  len = index(fmp,' ')-1
  open(7,file=fmp(1:len))
  do i=ndata+1,ndata+ndata_mp
    read(7,*) x(i),y(i),sig(i)
    x(i)=x(i)/1000.d0
    write(9,*) x(i)*1000.d0,y(i),sig(i)
  enddo
  close(7)
  write(9,100) '&'
  ndata=ndata+ndata_mp

  close(9)

  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine make_sim(x,ndata)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 x(ndatap)
  complex*16 ci
  real*8 lamda
  real*8 bx(maxlay+1),by(maxlay+1),bz(maxlay+1)
  common/data/ndata_pp,ndata_mm,ndata_pm,ndata_mp
  common/eff/pol1,pol2,fl1,fl2
  common/pol/poli(3),polf(3)
  common/pici/pi,ci
  common/wave/lamda,dlamda
  common/pos/q,sigmaq
  common/qy_ht/q_hr(max_hr),ref_hr(max_hr),q_max
  common/nlayer/nlay
  common/fields/bx,by,bz


  open(10,file='simulation')
  open(11,file='simulation_q')
  !      ++
  open(9,file='simulation_pp')
  poli(2)=pol1*fl1
  polf(2)=pol2
  q_max=4.d0*pi/lamda*dsin(x(ndata_pp))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=1,np_conv
    xx=x(ndata_pp)*i/dfloat(np_conv)
    y=refconv(xx)
    write(9,200) xx*1000.d0,y,q,sigmaq
    write(10,200) xx*1000.d0,y,q,sigmaq
    write(11,200) q,y,xx*1000.d0,sigmaq
  enddo
  nn=ndata_pp
  close(9)
  write(10,100) '&'
  write(11,100) '&'
  100  format(a1)

  !      --
  open(9,file='simulation_mm')
  poli(2)=-pol1
  polf(2)=-pol2*fl2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mm))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=1,np_conv
    xx=x(nn+ndata_mm)*i/dfloat(np_conv)
    y=refconv(xx)
    write(9,200) xx*1000.d0,y,q,sigmaq
    write(10,200) xx*1000.d0,y,q,sigmaq
    write(11,200) q,y,xx*1000.d0,sigmaq
  enddo
  nn=nn+ndata_mm
  close(9)
  write(10,100) '&'
  write(11,100) '&'

  !      +-
  open(9,file='simulation_pm')
  poli(2)=pol1*fl1
  polf(2)=-pol2*fl2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_pm))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=1,np_conv
    xx=x(nn+ndata_pm)*i/dfloat(np_conv)
    y=refconv(xx)
    write(9,200) xx*1000.d0,y,q,sigmaq
    write(10,200) xx*1000.d0,y,q,sigmaq
    write(11,200) q,y,xx*1000.d0,sigmaq
  enddo
  nn=nn+ndata_pm
  close(9)
  write(10,100) '&'
  write(11,100) '&'

  !      -+
  open(9,file='simulation_mp')
  poli(2)=-pol1
  polf(2)=pol2
  q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mp))+pdq
  do i=1,max_hr
    q_hr(i)=q_max*i/dfloat(max_hr)
    ref_hr(i)=polref_sp_rough(q_hr(i))
  enddo
  do i=1,np_conv
    xx=x(nn+ndata_mp)*i/dfloat(np_conv)
    y=refconv(xx)
    write(9,200) xx*1000.d0,y,q,sigmaq
    write(10,200) xx*1000.d0,y,q,sigmaq
    write(11,200) q,y,xx*1000.d0,sigmaq
  enddo
  nn=nn+ndata_mp
  close(9)
  write(10,100) '&'
  write(11,100) '&'

  close(10)
  close(11)

  write(8,*) 'end of make_sim'

  200  format(4f22.10)

  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
