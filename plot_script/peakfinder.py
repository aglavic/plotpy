#-*- coding: utf8 -*-
'''
  Peak finder algorithm based on the continuous wavelet transform (CWT) method
  discribed in:
    Du P, Kibbe WA, Lin SM.
    Improved peak detection in mass spectrum by incorporating continuous 
    wavelet transform-based pattern matching
    Bioinformatics 22(17) (2006)
'''

import numpy
from scipy.stats.mstats import mquantiles

class PeakFinder(object):
  '''
    Peak finder which can be reevaluated with different thresholds 
    without recalculation all steps.
    The steps performed are:
      - CWT of the dataset (which also removes the baseline)
      - Finding ridged lines by walking through different CWT scales
      - Calculate signal to noise ratio (SNR)
      - Identify the peaks from the ridged lines 
        (this is where the user parameters enter and can be recalculated fast) 
  '''

  def __init__(self,
               xdata, ydata,
               resolution=5,
               ):
    self.xdata=xdata
    self.ydata=ydata
    self.resolution=resolution
    self.positions=[]

    self._CWT()
    self._find_ridges()
    self._SNR()

  def _CWT(self):
    '''
      Create the continous wavelet transform for the dataset.
    '''
    self.CWT=MexicanHat(self.ydata,
                        largestscale=0.5,
                        notes=self.resolution,
                        order=1,
                        scaling='log',
                        )

  def _find_ridges(self, maxgap=4):
    '''
      Ridges are lines connecting local maxima at different
      scales of the CWT. Starting from the highest scale
      (most smooth) the lines are flowed down to the lowest
      scale. Strong peaks will produce longer ridge lines than
      weaker or noise, as they start at higher scales.
    '''
    cwt=self.CWT.getdata()
    scales=self.CWT.getscales()
    # initialize ridges starting at smoothest scaling
    ridges=[]
    gaps=[]
    cwt_len=len(cwt)
    for j, cwti in enumerate(reversed(cwt)):
      local_maxi=self._find_local_max(cwti)
      local_max_positions=numpy.where(local_maxi)[0]
      for i, ridge in enumerate(ridges):
        if gaps[i]<=maxgap:
          ridge_pos=ridge[-1][1]
          min_dist=numpy.abs(local_max_positions-ridge_pos).min()
          if min_dist<=scales[cwt_len-j]:
            idx=numpy.where(numpy.abs(local_max_positions-ridge_pos)==min_dist)[0][0]
            ridge.append([cwt_len-j-1, int(local_max_positions[idx])])
            gaps[i]=0
            local_max_positions[idx]=-1000
          else:
            gaps[i]+=1
      for ridge_pos in local_max_positions[local_max_positions>=0]: #@NoEffect
        gaps.append(0)
        ridges.append([[cwt_len-j-1, ridge_pos]])
    # collect some information on the ridge lines
    evaluated_ridges=[]
    ridge_info=[]
    ridge_intensities=[]
    for ridge in ridges:
      ridge=numpy.array(ridge)
      # len of ridge line and position of last point
      info=[ridge.shape[0], ridge[-1][1]]
      ridge_intensity=[]
      for rs, rx in ridge:
        ridge_intensity.append(cwt[rs, rx])
      ridge_intensity=numpy.array(ridge_intensity).real
      max_idx=numpy.where(ridge_intensity==ridge_intensity.max())[0][0]
      # scale of maximum coefficient on the ridge line
      #info.append(ridge[max_idx][0])
      info.append(scales[ridge[max_idx][0]])
      info.append(ridge_intensity[max_idx])
      ridge_info.append(info)
      ridge_intensities.append(ridge_intensity)
      evaluated_ridges.append(numpy.vstack([ridge[:, 0], ridge[:, 1], ridge_intensity]))
    self.ridges=evaluated_ridges
    self.ridge_info=ridge_info
    self.ridge_intensities=ridge_intensities

  def _SNR(self, minimum_noise_level=0.3):
    '''
      Calculate signal to nois ratio. Signal is the highest
      CWT intensity of all scales, noise is the 95% quantile
      of the lowest scale WT, which is dominated by noise.
    '''
    ridge_info=self.ridge_info
    cwt=self.CWT.getdata()
    minimum_noise=float(minimum_noise_level*mquantiles(
                        cwt[0].real,
                        0.95,
                        3./8., 3./8.))
    for info in ridge_info:
      scale=min(5, info[2])
      signal=info[3]
      base_left=min(0, (info[1]-scale*3))
      base_right=info[1]+scale*3
      noise=mquantiles(cwt[0][base_left:base_right+1].real,
                       0.95,
                       3./8., 3./8.)
      noise=numpy.nan_to_num(noise)
      noise=float(max([minimum_noise, noise]))
      info.append(signal/noise)

  def _find_local_max(self, data, steps=3):
    '''
      Find the positions of local maxima in a set of data.
      A window of size steps is used to check if the central
      point is the largest in the window region.
    '''
    if steps%2==0:
      steps+=1
    windows=[]
    for i in range(steps):
      windows.append(data[i:(-(steps-i-1) or None)])
    windows=numpy.vstack(windows)
    lmax=windows[(steps+1)/2-1]==windows.max(axis=0)
    return numpy.hstack([numpy.zeros(steps//2),
                         lmax,
                         numpy.zeros(steps//2)])

  def get_peaks(self, snr=2.5,
                min_width=None, max_width=None,
                ridge_length=15, analyze=False,
                double_peak_detection=False):
    '''
      Return a list of peaks fulfilling the defined conditions.
      
      @param snr: Minimal signal to noise ratio
      @param min_width: Minimal peak width
      @param max_width: Maximal peak width
      @param ridge_length: Minimal ridge line length
      @param analyze: Store information to analyze the filtering
      @param double_peak_detection: Perform a second run, where the 
                                    ridge_length is reduced near found peaks
    '''
    xdata=self.xdata
    if min_width is None:
      min_width=2.*abs(xdata[1]-xdata[0])
    if max_width is None:
      max_width=0.3*(xdata.max()-xdata.min())
    ridge_info=self.ridge_info

    if analyze:
      self.length_filtered=filter(lambda item: item[0]<ridge_length,
                     ridge_info)
      self.snr_filtered=filter(lambda item: item[4]<snr, ridge_info)
    # filter for minimum ridge line length
    ridge_info=filter(lambda item: item[0]>=ridge_length,
                     ridge_info)
    # filter for signal to noise ratio
    ridge_info=filter(lambda item: item[4]>=snr, ridge_info)
    # calculate peak info from ridge info
    # peak info items are [center_position, width, intensity]
    peak_info=[]
    for item in ridge_info:
      info=[]
      # x corresponding to index
      info.append(xdata[item[1]])
      # width corresponding to index width
      i_low=int(item[1]-item[2]/2)
      i_high=int(item[1]+item[2]/2)
      if i_low<0:
        i_low=0
      elif i_low==item[1]:
        i_low-=1
      if i_high>=len(xdata):
        i_high=len(xdata)-1
      elif i_high==item[1]:
        i_high+=1
      w_low=xdata[i_low]
      w_high=xdata[i_high]
      w=w_high-w_low
      info.append(float(abs(w))/1.6) # estimated peak width
      # intensity
      info.append(item[3]*1.41/numpy.sqrt(item[2]))
      # ridge length
      info.append(item[0])
      # SNR
      info.append(item[4])
      peak_info.append(info)
    # filter for peak width
    peak_info=filter(lambda item: (item[1]>=min_width)&(item[1]<=max_width),
                     peak_info)
    if analyze:
      width_filtered=zip(ridge_info, peak_info)
      self.width_filtered=filter(lambda item: \
              (item[1][1]>min_width)|(item[1][1]>max_width), width_filtered)
    peak_info.sort()
    if double_peak_detection:
      raise NotImplemented, "Double peak detection not available"
    return peak_info

  def visualize(self, snr=2.5,
                min_width=None, max_width=None,
                ridge_length=15):
    '''
      Use matplotlib to visualize the peak finding routine.
    '''
    from pylab import figure, plot, errorbar, pcolormesh, show, legend
    figure(101)
    peaks=self.get_peaks(snr, min_width, max_width, ridge_length, True)
    plot(self.xdata, self.ydata, 'r-', label='Data')
    errorbar([p[0] for p in peaks], [p[2] for p in peaks],
           xerr=[p[1] for p in peaks], fmt='go',
           elinewidth=2, barsabove=True, capsize=6,
           label='Detected Peaks', markersize=10)
    legend()
    figure(102)
    pcolormesh(self.CWT.getdata())
    peak_pos=[p[0] for p in peaks]
    snr_filtered=self.snr_filtered
    length_filtered=self.length_filtered
    #width_filtered=[item[0] for item in self.width_filtered]
    for ridge, ridge_info in reversed(zip(self.ridges, self.ridge_info)):
      if self.xdata[ridge[1][-1]] in peak_pos:
        plot(ridge[1], ridge[0], 'r-', linewidth=3)
      elif ridge_info in length_filtered:
        plot(ridge[1], ridge[0], 'g-', linewidth=2)
      elif ridge_info in snr_filtered:
        plot(ridge[1], ridge[0], 'b-', linewidth=2)
      else:
        plot(ridge[1], ridge[0], "y-")
    show()


if __name__=='__main__':
  # example
  from pylab import * #@UnusedWildImport
  x=numpy.linspace(-200, 400, 5000)
  gauss=lambda x, x0, sigma, I: I*numpy.exp(-0.5*((x-x0)/sigma)**2)
  y=gauss(x, 10, 5, 0.15)+gauss(x, 30, 0.5, 1)+\
    gauss(x, 55, 1, 1)+gauss(x, 75, 1, 0.3)+gauss(x, 90, 3, 0.2)
  ydata=y+numpy.random.normal(size=x.shape, scale=0.05)
  plot(x, ydata, 'r-', label='Data')
  plot(x, y, 'b-', linewidth=3, label='Theory')
  pf=PeakFinder(x, ydata)
  peaks=pf.get_peaks()
  errorbar([p[0] for p in peaks], [p[2] for p in peaks],
           xerr=[p[1] for p in peaks], fmt='go',
           elinewidth=2, barsabove=True, capsize=6,
           label='Peakfinder', markersize=10)
  #plot([p[0] for p in peaks], [p[2] for p in peaks],
  #         'go', markersize=10,
  #     label='Peakfinder')
  legend()
  show()


############## Code below here is adapted from an python CWT example ###########
'''
References:
A practical guide to wavelet analysis
C Torrance and GP Compo
Bull Amer Meteor Soc Vol 79 No 1 61-78 (1998)
naming below vaguely follows this.

updates:
(24/2/07):  Fix Morlet so can get MorletReal by cutting out H
(10/04/08): Numeric -> numpy
(25/07/08): log and lin scale increment in same direction!
            swap indices in 2-d coeffiecient matrix
            explicit scaling of scale axis
'''

class Cwt:
    """
    Base class for continuous wavelet transforms
    Implements cwt via the Fourier transform
    Used by subclass which provides the method wf(self,s_omega)
    wf is the Fourier transform of the wavelet function.
    Returns an instance.
    """

    fourierwl=1.00

    def _log2(self, x):
        # utility function to return (integer) log2
        return int(numpy.log(float(x))/numpy.log(2.0)+0.0001)

    def __init__(self, data, largestscale=1, notes=0, order=2, scaling='linear'):
        """
        Continuous wavelet transform of data

        data:    data in array to transform, length must be power of 2
        notes:   number of scale intervals per octave
        largestscale: largest scale as inverse fraction of length
                 of data array
                 scale = len(data)/largestscale
                 smallest scale should be >= 2 for meaningful data
        order:   Order of wavelet basis function for some families
        scaling: Linear or log
        """
        ndata=len(data)
        self.order=order
        self.scale=largestscale
        self._setscales(ndata, largestscale, notes, scaling)
        self.cwt=numpy.zeros((self.nscale, ndata), numpy.complex64)
        omega=numpy.array(range(0, ndata/2)+range(-ndata/2, 0))*(2.0*numpy.pi/ndata)
        datahat=numpy.fft.fft(data)
        self.fftdata=datahat
        #self.psihat0=self.wf(omega*self.scales[3*self.nscale/4])
        # loop over scales and compute wvelet coeffiecients at each scale
        # using the fft to do the convolution
        for scaleindex in range(self.nscale):
            currentscale=self.scales[scaleindex]
            self.currentscale=currentscale  # for internal use
            s_omega=omega*currentscale
            psihat=self.wf(s_omega)
            psihat=psihat*numpy.sqrt(2.0*numpy.pi*currentscale)
            convhat=psihat*datahat
            W=numpy.fft.ifft(convhat)
            self.cwt[scaleindex, 0:ndata]=W
        return

    def _setscales(self, ndata, largestscale, notes, scaling):
        """
        if notes non-zero, returns a log scale based on notes per ocave
        else a linear scale
        (25/07/08): fix notes!=0 case so smallest scale at [0]
        """
        if scaling=="log":
            if notes<=0: notes=1
            # adjust nscale so smallest scale is 2 
            noctave=self._log2(ndata/largestscale/2)
            self.nscale=notes*noctave
            self.scales=numpy.zeros(self.nscale, float)
            for j in range(self.nscale):
                self.scales[j]=ndata/(self.scale*(2.0**(float(self.nscale-1-j)/notes)))
        elif scaling=="linear":
            nmax=ndata/largestscale/2
            self.scales=numpy.arange(float(2), float(nmax))
            self.nscale=len(self.scales)
        else: raise ValueError, "scaling must be linear or log"
        return

    def getdata(self):
        """
        returns wavelet coefficient array
        """
        return self.cwt
    def getcoefficients(self):
        return self.cwt
    def getpower(self):
        """
        returns square of wavelet coefficient array
        """
        return (self.cwt*numpy.conjugate(self.cwt)).real
    def getscales(self):
        """
        returns array containing scales used in transform
        """
        return self.scales
    def getnscale(self):
        """
        return number of scales
        """
        return self.nscale

class MexicanHat(Cwt):
    """
    2nd Derivative Gaussian (mexican hat) wavelet
    """
    fourierwl=2.0*numpy.pi/numpy.sqrt(2.5)
    def wf(self, s_omega):
        # should this number be 1/sqrt(3/4) (no pi)?
        #s_omega = s_omega/self.fourierwl
        #print max(s_omega)
        a=s_omega**2
        b=s_omega**2/2
        return a*numpy.exp(-b)/1.1529702
        #return s_omega**2*numpy.exp(-s_omega**2/2.0)/1.1529702

