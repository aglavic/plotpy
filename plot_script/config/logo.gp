exp2d(x,y,a,b)=exp(-a*x**2-b*y**2)
line(x,y)= y<-5? exp2d(x,y+5,1,0.5): y<5? exp2d(x,0,1,1): exp2d(x,y-5,1,0.5)
halfcirc(x,y)= x<0? 0: exp( -(2.5-sqrt((x)**2+(y-2.5)**2))**2  )
p(x,y)= line(x,y)>halfcirc(x,y) ? -line(x,y): -halfcirc(x,y)
set cbrange [0:3]
set xrange [-3:5]
set yrange [-7:7]
# size 297 to get a 200px logo
set term png enhanced size 297,297
set output "logo.png"
unset border
unset key
unset colorbox
unset tics
set lmargin 0
set rmargin 0
set bmargin 0
set tmargin 0
set pm3d map
set isosamples 200
set palette rgbformulae 21,22,23
set size square
splot 1+p(x,y)+2*exp2d(x-1.25,y-2.5,2,2) w pm3d
