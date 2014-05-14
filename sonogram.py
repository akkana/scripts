#!/usr/bin/env python

# plot the waveform and a sonogram for an audio input (e.g. a bird song).

from pylab import *
from matplotlib import *
import wave
import sys

# modified specgram()
# http://stackoverflow.com/questions/19468923/cutting-of-unused-frequencies-in-specgram-matplotlib
def my_specgram(x, NFFT=256, Fs=2, Fc=0, detrend=mlab.detrend_none,
                window=mlab.window_hanning, noverlap=128,
                cmap=None, xextent=None, pad_to=None, sides='default',
                scale_by_freq=None, minfreq = None, maxfreq = None, **kwargs):
    """
    call signature::

      specgram(x, NFFT=256, Fs=2, Fc=0, detrend=mlab.detrend_none,
               window=mlab.window_hanning, noverlap=128,
               cmap=None, xextent=None, pad_to=None, sides='default',
               scale_by_freq=None, minfreq = None, maxfreq = None, **kwargs)

    Compute a spectrogram of data in *x*.  Data are split into
    *NFFT* length segments and the PSD of each section is
    computed.  The windowing function *window* is applied to each
    segment, and the amount of overlap of each segment is
    specified with *noverlap*.

    %(PSD)s

      *Fc*: integer
        The center frequency of *x* (defaults to 0), which offsets
        the y extents of the plot to reflect the frequency range used
        when a signal is acquired and then filtered and downsampled to
        baseband.

      *cmap*:
        A :class:`matplotlib.cm.Colormap` instance; if *None* use
        default determined by rc

      *xextent*:
        The image extent along the x-axis. xextent = (xmin,xmax)
        The default is (0,max(bins)), where bins is the return
        value from :func:`mlab.specgram`

      *minfreq, maxfreq*
        Limits y-axis. Both required

      *kwargs*:

        Additional kwargs are passed on to imshow which makes the
        specgram image

      Return value is (*Pxx*, *freqs*, *bins*, *im*):

      - *bins* are the time points the spectrogram is calculated over
      - *freqs* is an array of frequencies
      - *Pxx* is a len(times) x len(freqs) array of power
      - *im* is a :class:`matplotlib.image.AxesImage` instance

    Note: If *x* is real (i.e. non-complex), only the positive
    spectrum is shown.  If *x* is complex, both positive and
    negative parts of the spectrum are shown.  This can be
    overridden using the *sides* keyword argument.

    **Example:**

    .. plot:: mpl_examples/pylab_examples/specgram_demo.py

    """

    #####################################
    # modified  axes.specgram() to limit
    # the frequencies plotted
    #####################################

    # this will fail if there isn't a current axis in the global scope
    ax = gca()
    Pxx, freqs, bins = mlab.specgram(x, NFFT, Fs, detrend,
         window, noverlap, pad_to, sides, scale_by_freq)

    # modified here
    #####################################
    if minfreq is not None and maxfreq is not None:
        Pxx = Pxx[(freqs >= minfreq) & (freqs <= maxfreq)]
        freqs = freqs[(freqs >= minfreq) & (freqs <= maxfreq)]
    #####################################

    Z = 10. * np.log10(Pxx)
    Z = np.flipud(Z)

    if xextent is None: xextent = 0, np.amax(bins)
    xmin, xmax = xextent
    freqs += Fc
    extent = xmin, xmax, freqs[0], freqs[-1]
    im = ax.imshow(Z, cmap, extent=extent, **kwargs)
    ax.axis('auto')

    return Pxx, freqs, bins, im

def sonogram(wav_file, startsecs=None, endsecs=None):
    '''Plot a sonogram for the given file,
       optionally specifying the start and end time in seconds.
    '''
    wav = wave.open(wav_file, 'r')
    frames = wav.readframes(-1)
    frame_rate = wav.getframerate()
    chans = wav.getnchannels()
    secs = wav.getnframes() / float(frame_rate)
    sound_info = pylab.fromstring(frames, 'Int16')
    wav.close()

    # The wave module doesn't have any way to read just part of a wave file
    # (sigh), so we have to take an array slice after we've already read
    # the whole thing into numpy.
    if startsecs or endsecs:
        if not startsecs:
            startsecs = 0.0
        if not endsecs:
            endsecs = secs - startsecs

        startpos = startsecs * frame_rate * chans
        endpos = endsecs * frame_rate * chans
        sound_info = sound_info[startpos:endpos]
        secs = endsecs - startsecs
    else:
        startsecs = 0.0
    print secs, "seconds"

    t = arange(startsecs, startsecs + secs, 1.0 / frame_rate / chans)

    ax1 = subplot(211)
    title(wav_file)

    plot(t, sound_info)
    subplot(212, sharex=ax1)

    Pxx, freqs, bins, im = my_specgram(sound_info, Fs=frame_rate*chans,
                                       # cmap=cm.Accent,
                                       minfreq = 0, maxfreq = 10000)

    show()
    close()

if __name__ == '__main__':
    filename = sys.argv[1]
    start = None
    end = None
    if len(sys.argv) > 2:
        start = float(sys.argv[2])
        print "Starting at", start
    if len(sys.argv) > 3:
        end = float(sys.argv[3])
        print "ending at", end
    sonogram(filename, start, end)
