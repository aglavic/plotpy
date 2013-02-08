#!/bin/bash

# CPU dependent parameter for the gfortran compiler, for example
# i686 - standart PC Processor with at least PentiumPro instruction set
# athlon - AMD CPU with up to SSE insturctions
# athlon-fx - AMD Athlon with SSE2 and 64bit
# amdfam10 - AMD with up to SSE4A
# pentium-m - mobile intel CPU
# core2 - Intel core2 CPU
# find more in gcc man page
CPU="core2"

#CPUOPT="-mtune=$CPU"
CPUOPT="" #"-march=$CPU"

# Optimization level from 0 to 4, takes longer to compile and >=3 does only slightly increase the Program
OPTI="2"

# Get path of this script, so you do not have to set it by hand.
READL=$(readlink $0)
SCRIPTPATH=${READL%'/fit-script.sh'}

if [ ! $SCRIPTPATH/fit.f90 -ot $SCRIPTPATH/fit.o ] 
  then echo "Start compiling with -O$OPTI $CPUOPT"
  gfortran $SCRIPTPATH/fit.f90 -O$OPTI $CPUOPT -o $SCRIPTPATH/fit.o
  echo "Compiled"
fi

if [ $# -lt 3 -o $# -gt 4 ]
  then echo "Usage: fit-script.sh {data_file} {input_file} {output_file} [max_iterations]"
	echo "$1"
else echo "Input data: $1 Input file: $2 Output file: $3 Maximum iterations: ${4:-1000}"
  $SCRIPTPATH/fit.o $2 $1 $3.ref $3.sim ${4:-1000}
fi

#echo -e "$1\n$2\n$3\n">/var/tmp/commandline-input.tmp
