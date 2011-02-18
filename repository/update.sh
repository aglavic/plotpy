#!/bin/bash
FILE=`ls -t ../archiv/| head -1`
cp ../archiv/$FILE binary
dpkg-scanpackages binary /dev/null | gzip -9c > binary/Packages.gz
rsync -ruvz * ifflinux.iff.kfa-juelich.de:public_html/plotrepo
