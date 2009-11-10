subroutine mrqmin(x,y,sig,ndata,a,ma,lista,mfit,covar,alpha,chisq,alamda)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 x(ndatap),y(ndatap),sig(ndatap),a(map)
  integer*4 lista(map)
  real*8 covar(map,map)
  real*8 alpha(map,map),atry(map),beta(map),da(map),oneda(map,1)
  common/lamdafirst/alamda_first
  common/chi0/ochisq0
  common/layers/ntop,nincell,ncell,nbelow
  common/cons1/mfree,icons,itype_of_cons(map),i_para_ref(map)
  if(alamda.lt.0.d0)then
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
        read(*,*); write(8,*) 'mrqmin : improper permutation in lista'
      endif
    12       continue
    if (kk.ne.(ma+1)) read(*,*); write(8,*) 'mrqmin : improper permutation in lista'
      alamda=alamda_first
      write(8,*) 'alamda brought to',alamda
      call mrqcof(x,y,sig,ndata,a,ma,lista,mfit,alpha,beta,chisq,alamda)
      ochisq=chisq
      ochisq0=ochisq
      chi=dsqrt(chisq/dfloat(ndata-mfree))
      write(8,*) 'chi=',chi
      !!$        do 13 j=1,ma
      !!$          atry(j)=a(j)
      !!$13      continue
    endif
    do 13 j=1,ma
      atry(j)=a(j)
    13    continue
    do 15 j=1,mfit
      do 14 k=1,mfit
        covar(j,k)=alpha(j,k)
      14       continue
      covar(j,j)=alpha(j,j)*(1.d0+alamda)
      oneda(j,1)=beta(j)
    15    continue
    if(alamda.ne.0.d0) then
      call gaussj(covar,mfit,oneda,1)
      write(8,*) 'end of first gaussj in mrqmin'
      do j=1,mfit
        da(j)=oneda(j,1)
      enddo
    endif
    if(alamda.eq.0.d0) then
      write(8,*) 'begining of mrqcof in mrqmin for alamda=0'
      call mrqcof(x,y,sig,ndata,atry,ma,lista,mfit,covar,da,chisq,alamda)
      write(8,*) 'end of mrqcof in mrqmin for alamda=0'
      do j=1,mfit
        oneda(j,1)=da(j)
      enddo
      call gaussj(covar,mfit,oneda,1)
      write(8,*) 'end of second gaussj in mrqmin'
      call covsrt(covar,ma,lista,mfit)
      return
    endif
    do 16 j=1,mfit
      atry(lista(j))=a(lista(j))+da(j)
    16    continue
    if (atry(ma-3).lt.0.d0) atry(ma-3)=0.d0
    if (atry(ma-3).gt.1.d0) atry(ma-3)=1.d0
    if (atry(ma-2).lt.0.d0) atry(ma-2)=0.d0
    if (atry(ma-2).gt.1.d0) atry(ma-2)=1.d0
    if (atry(ma-1).lt.0.d0) atry(ma-1)=0.d0
    if (atry(ma-1).gt.1.d0) atry(ma-1)=1.d0
    if (atry(ma).lt.0.d0) atry(ma)=0.d0
    if (atry(ma).gt.1.d0) atry(ma)=1.d0
    write(8,*) 'proposed new parameters'
    np=0
    do i=1,ntop
      do j=1,7
        np=np+1
        write(8,*) np,' ',atry(np)
      enddo
      write(8,*)
    enddo
    do i=1,nincell
      do j=1,7
        np=np+1
        write(8,*) np,' ',atry(np)
      enddo
      write(8,*)
    enddo
    do i=1,nbelow
      do j=1,7
        np=np+1
        write(8,*) np,' ',atry(np)
      enddo
      write(8,*)
    enddo
    do j=1,6
      np=np+1
      write(8,*) np,' ',atry(np)
    enddo
    write(8,*)
    do j=1,2
      np=np+1
      write(8,*) np,' ',atry(np)
    enddo
    write(8,*)
    do j=1,4
      np=np+1
      write(8,*) np,' ',atry(np)
    enddo
    write(8,*)
    call mrqcof(x,y,sig,ndata,atry,ma,lista,mfit,covar,da,chisq,alamda)
    write(8,*) 'end of second mrqcof in mrqmin'
    if (chisq.lt.ochisq) then
      alamda=0.1d0*alamda
      ochisq=chisq
      do 18 j=1,mfit
        do 17 k=1,mfit
          alpha(j,k)=covar(j,k)
        17        continue
        beta(j)=da(j)
        a(lista(j))=atry(lista(j))
      18      continue
    else
      alamda=10.d0*alamda
      chisq=ochisq
    endif
    write(8,*) 'end of mrqmin'
    return
  end
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine covsrt(covar,ma,lista,mfit)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 covar(map,map)
  integer*4 lista(map)
  do 12 j=1,ma-1
    do 11 i=j+1,ma
      covar(i,j)=0.
    11      continue
  12    continue
  do 14 i=1,mfit-1
    do 13 j=i+1,mfit
      if(lista(j).gt.lista(i)) then
        covar(lista(j),lista(i))=covar(i,j)
      else
        covar(lista(i),lista(j))=covar(i,j)
      endif
    13      continue
  14    continue
  swap=covar(1,1)
  do 15 j=1,ma
    covar(1,j)=covar(j,j)
    covar(j,j)=0.
  15    continue
  covar(lista(1),lista(1))=swap
  do 16 j=2,mfit
    covar(lista(j),lista(j))=covar(1,j)
  16    continue
  do 18 j=2,ma
    do 17 i=1,j-1
      covar(i,j)=covar(j,i)
    17      continue
  18    continue
  return
end
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine gaussj(a,n,b,m)
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 a(map,map),b(map,1)
  integer*4 ipiv(map),indxr(map),indxc(map)
  do 11 j=1,n
    ipiv(j)=0
  11    continue
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
            read(*,*); write(8,*) 'gaussj : singular matrix'
          endif
        12          continue
      endif
    13      continue
    ipiv(icol)=ipiv(icol)+1
    if (irow.ne.icol) then
      do 14 l=1,n
        dum=a(irow,l)
        a(irow,l)=a(icol,l)
        a(icol,l)=dum
      14        continue
      do 15 l=1,m
        dum=b(irow,l)
        b(irow,l)=b(icol,l)
        b(icol,l)=dum
      15        continue
    endif
    indxr(i)=irow
    indxc(i)=icol
    if (a(icol,icol).eq.0.) read(*,*); write(8,*) 'gaussj : singular matrix 2.'
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
        18          continue
        do 19 l=1,m
          b(ll,l)=b(ll,l)-b(icol,l)*dum
        19          continue
      endif
    21      continue
  22    continue
  do 24 l=n,1,-1
    if(indxr(l).ne.indxc(l))then
      do 23 k=1,n
        dum=a(k,indxr(l))
        a(k,indxr(l))=a(k,indxc(l))
        a(k,indxc(l))=dum
      23        continue
    endif
  24    continue
  return
  end
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
subroutine mrqcof(x,y,sig,ndata,a,ma,lista,mfit,alpha,beta,chisq,alamda)
  !     new version for the constraints 
  use lay_parameters
  implicit real*8 (a-h,o-z)
  real*8 x(ndatap),y(ndatap),sig(ndatap),a(map),alpha(map,map),beta(map)
  integer*4 lista(map)
  real*8 dyda(map,ndatap),yplus(map,ndatap),da(map)
  complex*16 ci
  real*8 lamda
  real*8 bx(maxlay+1),by(maxlay+1),bz(maxlay+1)
  real*8 sc_pr(maxlay+1),bx_rough(0:maxlay+1),by_rough(0:maxlay+1),bz_rough(0:maxlay+1)
  common/valy/ymod(ndatap)
  common/cons1/mfree,icons,itype_of_cons(map),i_para_ref(map)
  common/cons2/n_para_eq_iref(map),nr_para_eq_iref(map,map),i_para_sum(map)
  common/pol/poli(3),polf(3)
  common/eff/pol1,pol2,fl1,fl2
  common/data/ndata_pp,ndata_mm,ndata_pm,ndata_mp
  common/qy_ht/q_hr(max_hr),ref_hr(max_hr),q_max
  common/pici/pi,ci
  common/wave/lamda,dlamda
  common/nlayer/nlay
  common/fields/bx,by,bz
  common/fields_rough/sc_pr,bx_rough,by_rough,bz_rough

  do 12 j=1,mfit
    do 11 k=1,j
      alpha(j,k)=0.d0
    11       continue
    beta(j)=0.d0
  12    continue


  chisq=0.d0
  if(alamda.ne.0.d0) then
    call param(a)
    !      ++
    poli(2)=pol1*f1
    polf(2)=pol2
    poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
    poli_norm=dsqrt(poli2)
    m=0
    bx_rough(m)=0.d0
    by_rough(m)=0.d0
    bz_rough(m)=0.d0
    do m=1,nlay+1
      sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
      if (sc_pr(m).ne.0.d0) then
        bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
      else
        bx_rough(m)=0.d0
        by_rough(m)=0.d0
        bz_rough(m)=0.d0
      endif
    enddo
    q_max=4.d0*pi/lamda*dsin(x(ndata_pp))+pdq
    do i=1,max_hr
      q_hr(i)=q_max*i/dfloat(max_hr)
      ref_hr(i)=polref_sp_rough(q_hr(i))
    enddo
    do i=1,ndata_pp
      ymod(i)=refconv(x(i))
      ymod(i)=dlog(ymod(i))/dlog(10.d0)
    enddo
    nn=ndata_pp
    !      --
    poli(2)=-pol1
    polf(2)=-pol2*fl2
    poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
    poli_norm=dsqrt(poli2)
    m=0
    bx_rough(m)=0.d0
    by_rough(m)=0.d0
    bz_rough(m)=0.d0
    do m=1,nlay+1
      sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
      if (sc_pr(m).ne.0.d0) then
        bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
      else
        bx_rough(m)=0.d0
        by_rough(m)=0.d0
        bz_rough(m)=0.d0
      endif
    enddo
    q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mm))+pdq
    do i=1,max_hr
      q_hr(i)=q_max*i/dfloat(max_hr)
      ref_hr(i)=polref_sp_rough(q_hr(i))
    enddo
    do i=nn+1,nn+ndata_mm
      ymod(i)=refconv(x(i))
      ymod(i)=dlog(ymod(i))/dlog(10.d0)
    enddo
    nn=nn+ndata_mm
    !      +-
    poli(2)=pol1*fl1
    polf(2)=-pol2*fl2
    poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
    poli_norm=dsqrt(poli2)
    m=0
    bx_rough(m)=0.d0
    by_rough(m)=0.d0
    bz_rough(m)=0.d0
    do m=1,nlay+1
      sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
      if (sc_pr(m).ne.0.d0) then
        bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
      else
        bx_rough(m)=0.d0
        by_rough(m)=0.d0
        bz_rough(m)=0.d0
      endif
    enddo
    q_max=4.d0*pi/lamda*dsin(x(nn+ndata_pm))+pdq
    do i=1,max_hr
      q_hr(i)=q_max*i/dfloat(max_hr)
      ref_hr(i)=polref_sp_rough(q_hr(i))
    enddo
    do i=nn+1,nn+ndata_pm
      ymod(i)=refconv(x(i))
      ymod(i)=dlog(ymod(i))/dlog(10.d0)
    enddo
    nn=nn+ndata_pm
    !      -+
    poli(2)=-pol1
    polf(2)=pol2
    poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
    poli_norm=dsqrt(poli2)
    m=0
    bx_rough(m)=0.d0
    by_rough(m)=0.d0
    bz_rough(m)=0.d0
    do m=1,nlay+1
      sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
      if (sc_pr(m).ne.0.d0) then
        bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
      else
        bx_rough(m)=0.d0
        by_rough(m)=0.d0
        bz_rough(m)=0.d0
      endif
    enddo
    q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mp))+pdq
    do i=1,max_hr
      q_hr(i)=q_max*i/dfloat(max_hr)
      ref_hr(i)=polref_sp_rough(q_hr(i))
    enddo
    do i=nn+1,nn+ndata_mp
      ymod(i)=refconv(x(i))
      ymod(i)=dlog(ymod(i))/dlog(10.d0)
    enddo
    write(8,*) 'ymod s calculated in mrqcof'

    !   calculation of the derivatives:
    mmfit=mfree
    do 13 j=1,mfree
      da(j)=a(lista(j))*1.d-2
      a(lista(j))=a(lista(j))+da(j)
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              a(nr_para_eq_iref(k,kk))=a(lista(j))
            enddo
          endif
          if (itype_of_cons(k).eq.2) then
            a(i_para_sum(k))=a(i_para_sum(k))-da(j)
          endif
        endif
      enddo
      call param(a)
      !      ++
      poli(2)=pol1*fl1
      polf(2)=pol2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(ndata_pp))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=1,ndata_pp
        yplus(lista(j),i)=refconv(x(i))
        yplus(lista(j),i)=dlog(yplus(lista(j),i))/dlog(10.d0)
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              do i=1,ndata_pp
                dyda(lista(mmfit+kk),i)=dyda(lista(j),i)
                yplus(lista(mmfit+kk),i)=yplus(lista(j),i)
              enddo
            enddo
          endif
          if (itype_of_cons(k).eq.2) then
            do i=1,ndata_pp
              dyda(lista(mmfit+1),i)=-dyda(lista(j),i)
              yplus(lista(mmfit+1),i)=yplus(lista(j),i)
            enddo
          endif
        endif
      enddo
      nn=ndata_pp
      !      --
      poli(2)=-pol1
      polf(2)=-pol2*fl2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mm))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_mm
        yplus(lista(j),i)=refconv(x(i))
        yplus(lista(j),i)=dlog(yplus(lista(j),i))/dlog(10.d0)
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              do i=nn+1,nn+ndata_mm
                dyda(lista(mmfit+kk),i)=dyda(lista(j),i)
                yplus(lista(mmfit+kk),i)=yplus(lista(j),i)
              enddo
            enddo
          endif
          if (itype_of_cons(k).eq.2) then
            do i=nn+1,nn+ndata_mm
              dyda(lista(mmfit+1),i)=-dyda(lista(j),i)
              yplus(lista(mmfit+1),i)=yplus(lista(j),i)
            enddo
          endif
        endif
      enddo            
      nn=nn+ndata_mm
      !      +-
      poli(2)=pol1*fl1
      polf(2)=-pol2*fl2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_pm))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_pm
        yplus(lista(j),i)=refconv(x(i))
        yplus(lista(j),i)=dlog(yplus(lista(j),i))/dlog(10.d0)
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              do i=nn+1,nn+ndata_pm
                dyda(lista(mmfit+kk),i)=dyda(lista(j),i)
                yplus(lista(mmfit+kk),i)=yplus(lista(j),i)
              enddo
            enddo
          endif
          if (itype_of_cons(k).eq.2) then
            do i=nn+1,nn+ndata_pm
              dyda(lista(mmfit+1),i)=-dyda(lista(j),i)
              yplus(lista(mmfit+1),i)=yplus(lista(j),i)
            enddo
          endif
        endif
      enddo            
      nn=nn+ndata_pm
      !      -+
      poli(2)=-pol1
      polf(2)=pol2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mp))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_mp
        yplus(lista(j),i)=refconv(x(i))
        yplus(lista(j),i)=dlog(yplus(lista(j),i))/dlog(10.d0)
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              do i=nn+1,nn+ndata_mp
                dyda(lista(mmfit+kk),i)=dyda(lista(j),i)
                yplus(lista(mmfit+kk),i)=yplus(lista(j),i)
              enddo
            enddo
            mmfit=mmfit+n_para_eq_iref(k)
          endif
          if (itype_of_cons(k).eq.2) then
            do i=nn+1,nn+ndata_mp
              dyda(lista(mmfit+1),i)=-dyda(lista(j),i)
              yplus(lista(mmfit+1),i)=yplus(lista(j),i)
            enddo
              mmfit=mmfit+1
          endif
        endif
      enddo            
      a(lista(j))=a(lista(j))-da(j)
      write(8,*) 'parameter:',lista(j),' ; dyda s calculated in mrqcof'
      do k=1,icons
        if (lista(j).eq.i_para_ref(k)) then
          if (itype_of_cons(k).eq.1) then
            do kk=1,n_para_eq_iref(k)
              a(nr_para_eq_iref(k,kk))=a(lista(j))
            enddo
            write(8,*) 'parameters:',lista(j),(nr_para_eq_iref(k,kk),kk=1,n_para_eq_iref(k)), &
            &     ': dyda s calculated in mrqcof'
          endif
          if (itype_of_cons(k).eq.2) then
            a(i_para_sum(k))=a(i_para_sum(k))+da(j)
            write(8,*) 'parameters:',lista(j),i_para_sum(k), &
            &      ' ; dyda s calculated in mrqcof'
          endif
        endif
      enddo
    13       continue
    if(mmfit.ne.mfit) then
      write(8,*) 'mfit=',mfit
      write(8,*) 'mmfit=',mmfit
      stop 'problem in enumerating the constraints in mrqcof'
    endif
  else
    do i=1,ndata
      ymod(i)=dexp(dlog(10.d0)*ymod(i))
    enddo
    do 8 j=1,mfit
      da(j)=a(lista(j))*1.d-2
      a(lista(j))=a(lista(j))+da(j)
      call param(a)
      !      ++
      poli(2)=pol1*fl1
      polf(2)=pol2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(ndata_pp))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=1,ndata_pp
        yplus(lista(j),i)=refconv(x(i))
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      nn=ndata_pp
      !      --
      poli(2)=-pol1
      polf(2)=-pol2*fl2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mm))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_mm
        yplus(lista(j),i)=refconv(x(i))
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      nn=nn+ndata_mm
      !      +-
      poli(2)=pol1*fl1
      polf(2)=-pol2*fl2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_pm))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_pm
        yplus(lista(j),i)=refconv(x(i))
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      nn=nn+ndata_pm
      !      -+
      poli(2)=-pol1
      polf(2)=pol2
      poli2=poli(1)*poli(1)+poli(2)*poli(2)+poli(3)*poli(3)
      poli_norm=dsqrt(poli2)
      m=0
      bx_rough(m)=0.d0
      by_rough(m)=0.d0
      bz_rough(m)=0.d0
      do m=1,nlay+1
        sc_pr(m)=(poli(1)*bx(m)+poli(2)*by(m)+poli(3)*bz(m))/poli_norm
        if (sc_pr(m).ne.0.d0) then
          bx_rough(m)=poli(1)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          by_rough(m)=poli(2)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
          bz_rough(m)=poli(3)/poli_norm*sc_pr(m)/dabs(sc_pr(m))
        else
          bx_rough(m)=0.d0
          by_rough(m)=0.d0
          bz_rough(m)=0.d0
        endif
      enddo
      q_max=4.d0*pi/lamda*dsin(x(nn+ndata_mp))+pdq
      do i=1,max_hr
        q_hr(i)=q_max*i/dfloat(max_hr)
        ref_hr(i)=polref_sp_rough(q_hr(i))
      enddo
      do i=nn+1,nn+ndata_mp
        yplus(lista(j),i)=refconv(x(i))
        dyda(lista(j),i)=(yplus(lista(j),i)-ymod(i))/da(j)
      enddo
      a(lista(j))=a(lista(j))-da(j)
      write(8,*) 'lista(j) =',lista(j),' ; dyda s calculated in mrqcof'
    8        continue
  endif

  if (alamda.ne.0.d0) then
    do 14 i=1,ndata
      sig2i=1.d0
      dy=dlog(y(i))/dlog(10.d0)-ymod(i)
      do 15 j=1,mfit
        wt=dyda(lista(j),i)*sig2i
        do 16 k=1,j
          alpha(j,k)=alpha(j,k)+wt*dyda(lista(k),i)
        16          continue
        beta(j)=beta(j)+dy*wt
      15        continue
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
        25          continue
        beta(j)=beta(j)+dy*wt
      24        continue
      chisq=chisq+dy*dy*sig2i
    23      continue
  endif
  do 17 j=2,mfit
    do 18 k=1,j-1
      alpha(k,j)=alpha(j,k)
    18    continue
  17    continue

  write(8,*) 'end of mrqcof'
  write(8,*)
  return
end
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
