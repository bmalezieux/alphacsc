
import os
import numpy as np
from scipy.signal import tukey

import mne
from sklearn.externals.joblib import Memory


mem = Memory(cachedir='.', verbose=0)


@mem.cache()
def load_data(sfreq, epoch=True, n_jobs=1):
    """Load and prepare the somato dataset for multiCSC


    Parameters
    ----------
    sfreq: float
        Sampling frequency of the signal. The data are resampled to match it.
    epoch : boolean
        If set to True, extract epochs from the raw data. Else, use the raw
        signal, divided in 10 chunks.
    n_jobs : int
        Number of jobs that can be used for preparing (filtering) the data.
    """
    data_path = os.path.join(mne.datasets.somato.data_path(), 'MEG', 'somato')
    raw = mne.io.read_raw_fif(
        os.path.join(data_path, 'sef_raw_sss.fif'), preload=True)
    raw.notch_filter(np.arange(50, 101, 50), n_jobs=n_jobs)
    raw.filter(2., None, n_jobs=n_jobs)

    if epoch:
        events = mne.find_events(raw, stim_channel='STI 014')

        event_id, t_min, t_max = 1, -2., 4.
        baseline = (None, 0)
        picks = mne.pick_types(raw.info, meg='grad', eeg=False, eog=True,
                               stim=False)

        epochs = mne.Epochs(raw, events, event_id, t_min, t_max,
                            picks=picks, baseline=baseline, reject=dict(
                                grad=4000e-13, eog=350e-6), preload=True)
        epochs.pick_types(meg='grad', eog=False)
        epochs.resample(sfreq, npad='auto')
        X = epochs.get_data()
        info = epochs.info

    else:
        raw.pick_types(meg='grad', eog=False)
        raw.resample(sfreq, npad='auto', n_jobs=n_jobs)
        X = raw.get_data()
        T = X.shape[-1]
        n_times = T // 10
        X = np.array([X[:, i * n_times:(i + 1) * n_times]
                      for i in range(10)])
        info = raw.info

    info['t_min'] = t_min
    # define n_chan, n_trials, n_times
    n_trials, n_chan, n_times = X.shape
    X *= tukey(n_times, alpha=0.1)[None, None, :]
    X /= np.std(X)
    return X, info
