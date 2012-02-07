# -*- encoding: utf-8 -*-
'''
 Settings used for parallel computing with the IPython cluster interface.
'''

__author__="Artur Glavic"
__credits__=[]
from plot_script.plotpy_info import __copyright__, __license__, __version__, __maintainer__, __email__ #@UnusedImport
__status__="Production"

import os


# keyword arguments of the Client function call
CLIENT_KW=dict(
            ## ZMQ url of path to .json file
            #url_or_file="tcp://192.168.2.2:37377", 
            #exec_key="bc0a6222-f7d8-4b61-9a3a-4113cb02cd86", 
            ### ipython profile of the cluster controller
            #profile='netcluster', 
            #profile_dir=None, 
            #sshserver='glavic@192.168.2.2', 
            timeout=5,
            #
           )

CLUSTER_PLOTPY_DIR=os.path.abspath(os.path.split(os.path.split(__file__)[0])[0])#"/home/glavic/plot-script"#
