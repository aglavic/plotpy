program fit_logspecrefgauss 
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3,ndatap=10000)
    real*8 lambda
    integer maximum_iter
    character*128 data_file,ent_file,res_output_file,sim_output_file,maximum_iterations
    dimension x(ndatap),y(ndatap),sig(ndatap),xxx(ndatap)
    dimension a(map),lista(map),covar(map,map),alpha(map,map)
    common/const/lambda,ma
    common/pipi/pi
    common/ninterf/nint
    common/const2/mfit
    common/ida/ida(map),icons,ii(map)
    common/cal/theta_max,width,rnorm
    common/file/res_output_file

    !! to avoid new compiling for every file, commandline options from
    call getarg(1,ent_file)
    call getarg(2,data_file)
    call getarg(3,res_output_file)
    call getarg(4,sim_output_file)
    call getarg(5,maximum_iterations)
    if(maximum_iterations.eq.'') then
        maximum_iter=1000
    else
        read(maximum_iterations,*) maximum_iter
    endif
    open(5,file=ent_file)
    open(8,file=res_output_file, ACCESS='SEQUENTIAL', FORM='FORMATTED')

    read (5,*) energy
    lambda=12398.4d0/energy
    read(5,*) ndata
    read(5,*)
    pi=dacos(-1.d0)
    open(7,file=data_file)
    do i=1,ndata
        read(7,*) xxx(i),y(i),sig(i)
        x(i)=xxx(i)
        ! write(8,*) x(i),' ',y(i),' ',sig(i)
    enddo
    close(7)
    write(8,*)
    write(8,*) 'wavelength =',lambda
    write(8,*)
    write(8,*)
    read(5,*) nint
    read(5,*)
    ma=0
    do i=2,nint
        read(5,*) a(ma+1)
        read(5,*) a(ma+2)
        read(5,*) a(ma+3)
        read(5,*) a(ma+4)
        read(5,*)
        ma=ma+4
    enddo
    read(5,*) a(ma+1)
    read(5,*) a(ma+2)
    read(5,*) a(ma+3)
    read(5,*)
    ma=ma+3
    read(5,*) a(ma+1)
    read(5,*) a(ma+2)
    read(5,*) a(ma+3)
    ma=ma+3
    write(8,*) 'total number of parameters :',ma
    write(8,*) 'initial parameters :'
    np=0
    do i=2,nint
        do j=1,4
            np=np+1
            write(8,*) np,' ',a(np)
        enddo
        write(8,*)
    enddo
    do j=1,3
        np=np+1
        write(8,*) np,' ',a(np)
    enddo
    write(8,*)
    do j=np+1,ma
        write(8,*) j,' ',a(j)
    enddo
    read(5,*)
    write(8,*)
    read(5,*) theta_max
    write(8,*) 'theta_max for recalibration :',theta_max
    theta_max=theta_max*pi/180.d0
    !!$     read(5,*) width
    !!$     write(8,*) 'gaussian width from the beam profile :',width
    !!$     width=width*pi/180.d0
    !!$     call qsimp2(0.d0,theta_max,rnorm)
    read(5,*)
    read(5,*) ifit
    write(8,*)
    write(8,*) 'ifit=',ifit
    if (ifit.eq.0) then
        close(5)
        goto 77
    endif
    read(5,*)
    read(5,*) mfit
    write(8,*)
    write(8,*) 'number of parameters fitted :',mfit
    write(8,*) 'indices of fitted parameters :'
    read(5,*) (lista(i),i=1,mfit)
    write(8,*)(lista(i),i=1,mfit)
    read(5,*) icons
    write(8,*) 'number of constraints :',icons
    nfree=mfit
    ncons=0
    do j=1,icons
        read(5,*) ii(j)
        write(8,*) 'number of parameters that must keep the same value:',ii(j)
        read(5,*) (ida(k),k=ncons+1,ncons+ii(j))
        write(8,*) 'list of those parameters:',(ida(k),k=ncons+1,ncons+ii(j))
        do k=ncons+2,ncons+ii(j)
            a(ida(k))=a(ida(ncons+1))
        enddo
        ncons=ncons+ii(j)
        nfree=nfree-ii(j)+1
    enddo
    write(8,*) 'number of free parameters=',nfree
    write(8,*)
    write(8,*)
    close(5)

    alamda=-1.d0
    iter=0
    write(8,*) 'iter=',iter,' alamda=',alamda
    call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
    write(8,*) 'kept parameters :'
    np=0
    do i=2,nint
        write(8,*) np+1,' ',a(np+1)
        write(8,*) np+2,' ',a(np+2)
        write(8,*) np+3,' ',a(np+3)
        write(8,*) np+4,' ',a(np+4)
        np=np+4
        write(8,*)
    enddo
    write(8,*) np+1,' ',a(np+1)
    write(8,*) np+2,' ',a(np+2)
    write(8,*) np+3,' ',a(np+3)
    np=np+3
    write(8,*)
    write(8,*) np+1,' ',a(np+1)
    write(8,*) np+2,' ',a(np+2)
    write(8,*) np+3,' ',a(np+3)
    write(8,*)
    chi=dsqrt(chisq)
    !     chi=dsqrt(chisq/dfloat(ndata-mfit+icons))
    write(8,*) ' chi=',chi
    write(8,*)
    write(8,*)
    itest=0
    do 10 iter=1,maximum_iter !maximum iterations, standart 1000
        write(8,*) '############################################################'
        write(8,*)
        write(8,*)
        write(8,*) 'iter=',iter,' itest=',itest,' alamda=',alamda
        write(8,*)
        chisq0=chisq
        call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
        close(8)
        open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')       
        write(8,*)
        write(8,*) 'kept parameters :'
        np=0
        do i=2,nint
            write(8,*) np+1,' ',a(np+1)
            write(8,*) np+2,' ',a(np+2)
            write(8,*) np+3,' ',a(np+3)
            write(8,*) np+4,' ',a(np+4)
            np=np+4
            write(8,*)
        enddo
        write(8,*) np+1,' ',a(np+1)
        write(8,*) np+2,' ',a(np+2)
        write(8,*) np+3,' ',a(np+3)
        np=np+3
        write(8,*)
        write(8,*) np+1,' ',a(np+1)
        write(8,*) np+2,' ',a(np+2)
        write(8,*) np+3,' ',a(np+3)
        write(8,*)
        open(9,file=sim_output_file)
        do i=1,1000
            xx=x(ndata)*i/1000.d0
            yy=refconv(xx,a)
            write(9,*) xx,' ',yy
        enddo
        close(9)
        !       chi=dsqrt(chisq/dfloat(ndata-mfit+icons))
        chi=dsqrt(chisq)
        write(8,*) ' chi=',chi
        write(8,*)
        write(8,*)
        dchisq=dabs(chisq-chisq0)/chisq0
        ! this was chisq.ge.chisq0 resulting in very long iterations
        ! don't know if this is correct too
        if (chisq.ge.chisq0.and.alamda.le.1.0d10) then
            itest=0
        else if (dchisq.le.1.0d-2.or.alamda.gt.1.0d10) then
            itest=itest+1
        endif
        if (itest.eq.5) goto 88
10  continue
88  if (iter.lt.1000) then
        alamda=0.d0
        write(8,*) 'itest=',itest,' alamda=',alamda
        call mrqmin (x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
        write(8,*) 'list of parameters:'
        write(8,*) 'chi2= ',chisq
        chi=dsqrt(chisq/dfloat(ndata-mfit+icons))
        write(8,*) 'normalized chi= ',chi
        write(8,*) 'fit obtained in ', iter,' iterations'
        write(8,*) 'list of parameters with uncertaincies multiplied by morm. chi :'
        np=0
        do i=2,nint
            write(8,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
            write(8,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
            write(8,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
            write(8,100) np+4,' ',a(np+4),' +/- ',dsqrt(covar(np+4,np+4))*chi
            np=np+4
            write(8,*)
        enddo
        write(8,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
        write(8,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
        write(8,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
        np=np+3
        write(8,*)
        write(8,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
        write(8,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
        write(8,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
        !!$       write(8,*)
        !!$       write(8,*) 'covariance matrix :' 
        !!$       do i=1,mfit
        !!$         write(8,500) (covar(lista(i),lista(j)),j=1,mfit)
        !!$       enddo
        ! open(4,file='param')
        ! np=0
        ! do i=2,nint
        !   write(4,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
        !   write(4,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
        !   write(4,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
        !   write(4,100) np+4,' ',a(np+4),' +/- ',dsqrt(covar(np+4,np+4))*chi
        !   np=np+4
        !   write(4,*)
        ! enddo
        ! write(4,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
        ! write(4,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
        ! write(4,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
        ! np=np+3
        ! write(4,*)
        ! write(4,100) np+1,' ',a(np+1),' +/- ',dsqrt(covar(np+1,np+1))*chi
        ! write(4,100) np+2,' ',a(np+2),' +/- ',dsqrt(covar(np+2,np+2))*chi
        ! write(4,100) np+3,' ',a(np+3),' +/- ',dsqrt(covar(np+3,np+3))*chi
        ! close(4)
    else
        write(8,*) 'not enough iterations, iter=',iter
    endif
100 format(10x,i3,a1,f13.5,a5,f13.5)
500 format(50f10.5)
    write(8,*)
    write(8,*) 'results generated with program "fit_logspecrefgauss.f90"'   


77  close(8)
    open(9,file=sim_output_file)
    do i=1,1000
        xx=x(ndata)*i/1000.d0
        yy=refconv(xx,a)
        write(9,*) xx,' ',yy
    enddo
    close(9)
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
function refconv(q,a)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    dimension a(map)
    real*8 lambda
    common/const/lambda,ma
    common/pipi/pi
    common/ninterf/nint
    common/pos/qq,sigma

    qq=q
    sigma=dabs(a(ma-1))*1.d-3
    if (sigma.lt.1.d-6) then
        yy=ref(q,a)
    else
        call qsimp(q-4.d0*sigma,q+4.d0*sigma,yy,a)
        yy=yy/(dsqrt(2.d0*pi)*sigma)
    endif
    yy=yy*dabs(a(ma))*1.0d6
    refconv=yy+dabs(a(ma-2))
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine qsimp(x1,x2,s,a)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    parameter(eps=1.d-2,jmax=30)
    dimension a(map)

    ost=-1.d30
    os= -1.d30
    it_extern=0d0 ! inserted by Artur Glavic to get it as global variable, not a clean solution
    do 11 j=1,jmax
        call trapzd(x1,x2,st,j,a,it_extern)
        s=(4.d0*st-ost)/3.d0
        if (abs(s-os).lt.eps*abs(os)) return
        os=s
        ost=st
11  continue
    write(*,*) 'qsimp : too many steps.'
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine trapzd(x1,x2,s,n,a,it)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    dimension a(map)

    if (n.eq.1) then
        s=0.5d0*(x2-x1)*(gaussref(x1,a)+gaussref(x2,a))
        it=1
    else
        tnm=it;
        del=(x2-x1)/tnm
        x=x1+0.5d0*del
        sum=0.d0
        do 11 j=1,it
            sum=sum+gaussref(x,a)
            x=x+del
11     continue
        s=0.5d0*(s+(x2-x1)*sum/tnm)
        it=2*it
    endif
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
function gaussref(x,a)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    dimension a(map)
    common/pos/q,sigma

    gaussref=dexp(-(x-q)*(x-q)/(2.d0*sigma*sigma))*ref(x,a)
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
function ref(q,a)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    dimension a(map)
    real*8 lambda
    dimension z(maxint),delta(maxint+1),beta(maxint+1),sigma(maxint)
    complex*16 ci,index,r
    complex*16 x(maxint+1),kz(maxint+1)
    common/const/lambda,ma
    common/pipi/pi
    common/ninterf/nint
    common/cal/theta_max,width,rnorm

    ci=dcmplx(0.d0,1.d0)
    alpha=dasin(q*lambda/4.d0/pi)

    z(1)=0.d0
    delta(1)=0.d0
    beta(1)=0.d0
    mma=0
    do j=2,nint
        z(j)=z(j-1)-dabs(a(mma+1))
        delta(j)=a(mma+2)*1.d-6
        beta(j)=delta(j)/dabs(a(mma+3))
        sigma(j-1)=dabs(a(mma+4))
        mma=mma+4
    enddo
    delta(nint+1)=a(mma+1)*1.d-6
    beta(nint+1)=delta(j)/dabs(a(mma+2))
    sigma(nint)=dabs(a(mma+3))

    do j=1,nint+1
        index=dcmplx(1.d0-delta(j),beta(j))
        kz(j)=2.d0*pi/lambda*cdsqrt((index**2-dcos(alpha)**2))
    enddo

    x(nint+1)=dcmplx(0.d0,0.d0)
    do j=nint,1,-1
        r=(kz(j)-kz(j+1))/(kz(j)+kz(j+1))
        r=r*cdexp(-2.d0*sigma(j)*sigma(j)*kz(j)*kz(j+1))
        x(j)=cdexp(-2.d0*ci*kz(j)*z(j))
        x(j)=x(j)*(r+x(j+1)*cdexp(2.d0*ci*kz(j+1)*z(j)))/(1.d0+r*x(j+1)*cdexp(2.d0*ci*kz(j+1)*z(j)))
    enddo
    y=cdabs(x(1))**2

    if (alpha.lt.theta_max) then
        !!$       call qsimp2(0.d0,alpha,calfact)
        !!$       calfact=calfact/rnorm
        calfact=alpha/theta_max
        ref=y*calfact
    else
        ref=y
    endif
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine qsimp2(x1,x2,s)
    implicit real*8 (a-h,o-z)
    parameter(eps=1.d-2,jmax=20)

    ost=-1.d30
    os= -1.d30
    it_extern=0d0 ! inserted by Artur Glavic to get it as global variable, not a clean solution
    do 11 j=1,jmax
        call trapzd2(x1,x2,st,j,it_extern)
        s=(4.d0*st-ost)/3.d0
        if (abs(s-os).lt.eps*abs(os)) return
        os=s
        ost=st
11  continue
    write(*,*) 'qsimp2 : too many steps.'
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine trapzd2(x1,x2,s,n,it)
    implicit real*8 (a-h,o-z)

    if (n.eq.1) then
        s=0.5d0*(x2-x1)*(gauss(x1)+gauss(x2))
        it=1
    else
        tnm=it
        del=(x2-x1)/tnm
        x=x1+0.5d0*del
        sum=0.d0
        do 11 j=1,it
            sum=sum+gauss(x)
            x=x+del
11     continue
        s=0.5d0*(s+(x2-x1)*sum/tnm)
        it=2*it
    endif
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
function gauss(x)
    implicit real*8 (a-h,o-z)
    common/cal/theta_max,width,rnorm

    gauss=dexp(-x*x/(2.d0*width*width))
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine mrqmin(x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
    implicit real*8 (a-h,o-z)
    parameter (maxint=25,map=4*maxint+3)
    parameter(ndatap=10000)
    dimension x(ndatap),y(ndatap),sig(ndatap),a(map),lista(map),covar(map,map)
    dimension alpha(map,map),atry(map),beta(map),da(map),oneda(map,1)
    character*128 res_output_file
    common/ninterf/nint
    common/file/res_output_file
    common/global_maps/atry,beta,da,oneda
    common/global_ochisq/ochisq

    close(8)
    open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')             
    if(alamda.lt.0.d0) then
        kk=mfit+1
        do 12 j=1,ma
            ihit=0
            do 11 k=1,mfit
                if(lista(k).eq.j)ihit=ihit+1
11          continue
            if (ihit.eq.0) then
                lista(kk)=j
                kk=kk+1
            else if (ihit.gt.1) then
                write(*,*) 'mrqmin : improper permutation in lista'
            endif
12      continue
        if (kk.ne.(ma+1)) write(*,*) 'mrqmin : improper permutation in lista'
        alamda=0.001d0
        write(8,*) 'begin of first mrqcof in mrqmin'
        close(8)
        open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')             
        call mrqcof(x,y,sig,ndata,a,ma,lista,mfit,alpha,beta,chisq,alamda)
        write(8,*) 'end of first mrqcof in mrqmin'
        ochisq=chisq
        chi0=dsqrt(ochisq)
        write(8,*) 'chi0=',chi0
        !!$        do 13 j=1,ma
        !!$          atry(j)=a(j)
        !!$13      continue
    endif
    do 13 j=1,ma
        atry(j)=a(j)
13  continue
    do 15 j=1,mfit
        do 14 k=1,mfit
            covar(j,k)=alpha(j,k)
14      continue
        covar(j,j)=alpha(j,j)*(1.d0+alamda)
        oneda(j,1)=beta(j)
15  continue
    if(alamda.ne.0.d0) then
        call gaussj(covar,mfit,oneda,1)
        do j=1,mfit
            da(j)=oneda(j,1)
        enddo
    endif
    if(alamda.eq.0.d0) then
        write(8,*) 'begin of second mrqcof in mrqmin'
        close(8)
        open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')               
        call mrqcof(x,y,sig,ndata,atry,ma,lista,mfit,covar,da,chisq,alamda)
        write(8,*) 'end of second mrqcof in mrqmin'
        do j=1,mfit
            oneda(j,1)=da(j)
        enddo
        call gaussj(covar,mfit,oneda,1)
        call covsrt(covar,ma,lista,mfit)
        return
    endif
    do 16 j=1,mfit
        atry(lista(j))=a(lista(j))+da(j)
16  continue
    write(8,*) 'proposed new parameters :'
    np=0
    do i=2,nint
        do j=1,4
            np=np+1
            write(8,*) np,' ',atry(np)
        enddo
        write(8,*)
    enddo
    do j=1,3
        np=np+1
        write(8,*) np,' ',atry(np)
    enddo
    write(8,*)
    do j=np+1,ma
        write(8,*) j,' ',atry(j)
    enddo
    write(8,*)
    write(8,*) 'begin of third mrqcof in mrqmin'
    close(8)
    open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')       
    call mrqcof(x,y,sig,ndata,atry,ma,lista,mfit,covar,da,chisq,alamda)
    write(8,*) 'end of third mrqcof in mrqmin'
    if (chisq.lt.ochisq) then
        alamda=0.1d0*alamda
        ochisq=chisq
        do 18 j=1,mfit
            do 17 k=1,mfit
                alpha(j,k)=covar(j,k)
17          continue
            beta(j)=da(j)
            a(lista(j))=atry(lista(j))
18      continue
    else
        alamda=10.d0*alamda
        chisq=ochisq
    endif
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine covsrt(covar,ma,lista,mfit)
    implicit real*8 (a-h,o-z)
    parameter (maxint=25,map=4*maxint+3)
    dimension covar(map,map),lista(map)

    do 12 j=1,ma-1
        do 11 i=j+1,ma
            covar(i,j)=0.
11      continue
12  continue
    do 14 i=1,mfit-1
        do 13 j=i+1,mfit
            if(lista(j).gt.lista(i)) then
                covar(lista(j),lista(i))=covar(i,j)
            else
                covar(lista(i),lista(j))=covar(i,j)
            endif
13      continue
14  continue
    swap=covar(1,1)
    do 15 j=1,ma
        covar(1,j)=covar(j,j)
        covar(j,j)=0.
15  continue
    covar(lista(1),lista(1))=swap
    do 16 j=2,mfit
        covar(lista(j),lista(j))=covar(1,j)
16  continue
    do 18 j=2,ma
        do 17 i=1,j-1
            covar(i,j)=covar(j,i)
17      continue
18  continue
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine gaussj(a,n,b,m)
    implicit real*8 (a-h,o-z)
    parameter (maxint=25,map=4*maxint+3)
    dimension a(map,map),b(map,1),ipiv(map),indxr(map),indxc(map)

    do 11 j=1,n
        ipiv(j)=0
11  continue
    do 22 i=1,n
        big=0.d0
        do 13 j=1,n
            if(ipiv(j).ne.1)then
                do 12 k=1,n
                if (ipiv(k).eq.0) then
                    if (dabs(a(j,k)).ge.big)then
                        big=dabs(a(j,k))
                        irow=j
                        icol=k
                    endif
                else if (ipiv(k).gt.1) then
                    write(*,*) 'gaussj : singular matrix'
                endif
12              continue
            endif
13      continue
        ipiv(icol)=ipiv(icol)+1
        if (irow.ne.icol) then
            do 14 l=1,n
                dum=a(irow,l)
                a(irow,l)=a(icol,l)
                a(icol,l)=dum
14          continue
            do 15 l=1,m
                dum=b(irow,l)
                b(irow,l)=b(icol,l)
                b(icol,l)=dum
15          continue
        endif
        indxr(i)=irow
        indxc(i)=icol
        if (a(icol,icol).eq.0.d0) write(*,*) 'gaussj : singular matrix 2.'
        pivinv=1.d0/a(icol,icol)
        a(icol,icol)=1.d0
        do 16 l=1,n
            a(icol,l)=a(icol,l)*pivinv
16      continue
        do 17 l=1,m
            b(icol,l)=b(icol,l)*pivinv
17      continue
        do 21 ll=1,n
            if(ll.ne.icol)then
                dum=a(ll,icol)
                a(ll,icol)=0.d0
                do 18 l=1,n
                    a(ll,l)=a(ll,l)-a(icol,l)*dum
18              continue
                do 19 l=1,m
                  b(ll,l)=b(ll,l)-b(icol,l)*dum
19              continue
            endif
21      continue
22  continue
    do 24 l=n,1,-1
    if(indxr(l).ne.indxc(l))then
    do 23 k=1,n
    dum=a(k,indxr(l))
    a(k,indxr(l))=a(k,indxc(l))
    a(k,indxc(l))=dum
    23        continue
    endif
    24    continue
    write(8,*) 'end of gaussj'
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine mrqcof(x,y,sig,ndata,a,ma,lista,mfit,alpha,beta,chisq,alamda)
    implicit real*8 (a-h,o-z)
    parameter(maxint=25,map=4*maxint+3)
    parameter(ndatap=10000)
    dimension x(ndatap),y(ndatap),sig(ndatap),alpha(map,map),beta(map),lista(map),a(map)
    dimension dyda(map,ndatap)
    dimension dydap(map,ndatap)
    character*128 res_output_file
    common/valder/ymod(ndatap),yplus(map,ndatap),da(map),dyda1(map,ndatap)
    common/ida/ida(map),icons,ii(map)
    common/file/res_output_file

    do 12 j=1,mfit
        do 11 k=1,j
            alpha(j,k)=0.d0
11      continue
        beta(j)=0.d0
12  continue
    chisq=0.d0
    if(alamda.ne.0.d0) then
        do i=1,ndata
            ymod(i)=refconv(x(i),a)
            ymod(i)=dlog(ymod(i))/dlog(10.d0)
        enddo
        do 10 j=1,mfit
            da(j)=a(lista(j))*1.d-5
            a(lista(j))=a(lista(j))+da(j)/2.d0
            do i=1,ndata
            yplus(lista(j),i)=refconv(x(i),a)
            yplus(lista(j),i)=dlog(yplus(lista(j),i))/dlog(10.d0)
            dyda1(lista(j),i)=(yplus(lista(j),i)-ymod(i))/(da(j)/2.d0)
            enddo
            a(lista(j))=a(lista(j))-da(j)/2.d0
10      continue   
        write(8,*) 'dyda s before the constraints'
        do 13 j=1,mfit
            write(8,*) lista(j),dyda1(lista(j),1),dyda1(lista(j),ndata+1)
            close(8)
            open(8,file=res_output_file, ACCESS='APPEND', FORM='FORMATTED')       
13      continue
    else
        do i=1,ndata
            ymod(i)=dexp(dlog(10.d0)*ymod(i))
            do j=1,mfit
                yplus(lista(j),i)=dexp(dlog(10.d0)*yplus(lista(j),i))
                dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/(da(j)/2.d0)
            enddo
        enddo
    endif
    if(icons.eq.0.and.alamda.ne.0.d0) then
        do j=1,mfit
            do i=1,ndata
                dyda(lista(j),i)=dyda1(lista(j),i)
            enddo
        enddo
    endif

    ! taking into account the constraints :
    if(icons.gt.0.and.alamda.ne.0.d0) then
        do j=1,mfit
            do i=1,ndata
                dydap(lista(j),i)=dyda1(lista(j),i)
            enddo
        enddo
        do 4 j=1,mfit
            ncons=0
            do 3 k=1,icons
                do 2 l=ncons+1,ncons+ii(k)
                    if (lista(j).eq.ida(l)) then
                        do i=1,ndata
                            dydap(lista(j),i)=0.d0
                        enddo
                        do m=1,ii(k)
                            !                  write(8,*) 'lista(j),ida(ncons+m)=',lista(j),ida(ncons+m)
                            do i=1,ndata
                                dydap(lista(j),i)=dydap(lista(j),i)+dyda1(ida(ncons+m),i)/ii(k)*1.d0
                            enddo
                        enddo
                        goto 4
                    endif
2               continue
                ncons=ncons+ii(k)
3           continue
4       continue
        do j=1,mfit
            do i=1,ndata
                dyda(lista(j),i)=dydap(lista(j),i)
            enddo
        enddo
        write(8,*) 'new dyda s after taking into account the constraints'
        do 7 j=1,mfit
            write(8,*) lista(j),dyda(lista(j),1),dyda(lista(j),ndata+1)
7       continue
    endif

    if (alamda.ne.0.d0) then
        do 14 i=1,ndata
            sig2i=1.d0
            dy=dlog(y(i))/dlog(10.d0)-ymod(i)
            do 15 j=1,mfit
                wt=dyda(lista(j),i)*sig2i
                do 16 k=1,j
                    alpha(j,k)=alpha(j,k)+wt*dyda(lista(k),i)
16              continue
                beta(j)=beta(j)+dy*wt
15          continue
            chisq=chisq+dy*dy*sig2i
14      continue
    else
        do 23 i=1,ndata
            sig2i=1.d0/(sig(i)*sig(i))
            dy=y(i)-ymod(i)
            do 24 j=1,mfit
                wt=dyda(lista(j),i)*sig2i
                do 25 k=1,j
                    alpha(j,k)=alpha(j,k)+wt*dyda(lista(k),i)
25              continue
                beta(j)=beta(j)+dy*wt
24          continue
            chisq=chisq+dy*dy*sig2i
23      continue
    endif
    do j=2,mfit
        do k=1,j-1
            alpha(k,j)=alpha(j,k)
        enddo
    enddo
    write(8,*) 'end of mrqcof'
    return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
