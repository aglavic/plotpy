function refconv(theta)
  use lay_parameters
     implicit real*8 (a-h,o-z)
     complex*16 ci
     real*8 lamda,illu
     integer*4 delta_n
     common/pici/pi,ci
     common/wave/lamda,dlamda
     common/pos/q,sigmaq
     common/reso/s1,s2,sl,d1,d2
     common/calbg/cal,bg
     common/qy_ht/q_hr(max_hr),ref_hr(max_hr),q_max

     q=4*pi/lamda*dsin(theta)
     dtheta1=(s1+s2)/(d1-d2)
     dtheta2=(s1+sl*dsin(theta))/d1
     dtheta1=dtheta1/2.d0 ! from FW to FWHM
     dtheta2=dtheta2/2.d0
     dtheta=dmin1(dtheta1,dtheta2)
     dtheta=dtheta/2.35d0 ! from FWHM to rms
     sigmaq=dsqrt((4.d0*pi/lamda*dcos(theta)*dtheta)**2+(4.d0*pi/lamda**2*dsin(theta)*dlamda)**2)

!    integration from -4*sigmaq to +4*sigmaq
     delta_n=idint(4.d0*sigmaq/q_max*dfloat(max_hr))
     nq=idint(q/q_max*dfloat(max_hr))
!     write(6,*) 'nq,delta_n',nq,delta_n
     dq=q_max/dfloat(max_hr)
     refconv=0.d0
     do 10 i=nq-delta_n,nq+delta_n
        if (i.lt.1) goto 10
        if (i.gt.max_hr) goto 10
        refconv=refconv+dexp(-(q_hr(i)-q)**2/2.d0/sigmaq**2)*ref_hr(i)*dq
10   continue
     refconv=refconv/dsqrt(2.d0*pi)/sigmaq

     refconv=illu(theta)*refconv*cal+bg
     return
     end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
     function illu(theta)
     implicit real*8 (a-h,o-z)
     common/reso/s1,s2,sl,d1,d2
     real*8 illu,illu_max
     real*8 l

     l=d1-d2
     d=d2

     a=dabs(s2/2.d0+d/2.d0/l*(s2-s1))
     alpha_g=(s1+s2)/l
     b=0.5d0*(s2+alpha_g*d)
     
     illu_max=a+b

     p=sl*dsin(theta)
     if(p.le.2.d0*a) then
        illu=p/illu_max
        goto 10
     endif
     if((p.gt.2.d0*a).and.(p.le.2.d0*b)) then
        illu=2.d0*(a+1.d0/(8.d0*(a-b))*(p**2-4.d0*b*p-4.d0*a**2+8.d0*a*b))/illu_max
        goto 10
     endif
     if(p.gt.2.d0*b) then
        illu=1.d0
     endif
10   return
     end function illu
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
