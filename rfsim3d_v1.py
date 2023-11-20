# -*- coding: utf-8 -*-
"""RFsim3d_v1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oQKSKmqs7zwu40x7_nuD-Fw6U1Ci0x3Y

# Explantions

## 1. **Random Sampling (CPU)**:
The full list of all possible sampling in numpy can be found in the following [link](https://numpy.org/doc/1.16/reference/routines.random.html).
## 2. **GPU computation**:
GPU computation of the random field is given by [Cupy](https://cupy.dev/).

##  3. **Simulation of Gaussian Random Field**

  - Generate the (normal distributed) white noise field $\langle n(\vec x) n(\vec y) \rangle \propto \delta^3(\vec x, \vec y)$.

  - Perform Fast Fourier transform to obtain noise field of unit amplitude $\langle n(\vec k) n(-\vec k) \rangle = 1$

  - Obtain the fourier ampltide by multiplying the white noise field with the
 power spectrum:
$\langle \phi(\vec k)\phi(-\vec k)\rangle'=\langle n(\vec k) n(-\vec k) \rangle \times P(k)$ for $P(k) \equiv {A}{ \lvert k \rvert^{-d}}$.
  - Inverse Fast Fourier transform to obtain the gaussian field.

  - References: Gaussian Random Field is constructed out of [the following website](https://garrettgoon.com/gaussian-fields/).

### **Parameters for Field Simulation:**

- `amplitude`: amplitude of spectrum $A$
- `k_power` : power law of the spectrum $d$
- `pixel` : pixels, size of the plots
- `mean` : mean of the gaussian distribution
- `std_dev` : standard deviation of the gaussian distribution
- `decay_rate` : decay rate of the exponential distribution
- `expected_occurrences_rate ` : expected occurrences rate of the poisson distribution

## 4. **Clustering Algorithm**
### 4.1 **Density-based spatial clustering of applications with noise (DBSCAN)**:
  This algorithm defines clusters as continuous regions of high density.
  - For each instance, the algorithm counts the number of instances within a small distance ϵ (*epsilon*). This region is called the instance’s ϵ-neighborhood.
  - If an instance has at least min_samples instances within its ϵ-neighborhood (includingitself), then it is considered a core instance. Core instances are those that are located in dense regions.
  - All instances in the neighborhood of a core instance belong to the same cluster. This neighborhood may include other core instances; therefore, a long sequence of neighboring core instances forms a single cluster.
  - Any instance that is not a core instance and does not have one in its neighborhood is considered an anomaly.

### **Parameters**
  - `eps` : distance parameter $ϵ$
  - `min_samples` : Minimum amount of instasnces required in a $ϵ$ neighborhood
  - `Cluster -1` : Instances that are not a core instance. Marked in black color.
"""

# @title Import packages

#import cupy as cp
import numpy as np
import matplotlib.pyplot as plt
import gc

from scipy.special import erf

"""# 1. Define functions"""

# @title 1.2 Random field simulations

def gpu_grf_3d(white_noise, pixel, z_pixel, amplitude, k_power):
    # Transfer white noise to GPU
    white_noise_gpu = cp.asarray(white_noise)

    # 3D Fast Fourier transform of the white noise
    fft_white_noise = cp.fft.fftn(white_noise_gpu)

    # Generating FFT momentum
    kx = cp.fft.fftfreq(pixel)*pixel
    ky = cp.fft.fftfreq(pixel)*pixel
    kz = cp.fft.fftfreq(z_pixel)*z_pixel

    # Genearting FFT momentum 3D array
    kx_grid, ky_grid, kz_grid = cp.meshgrid(kx, ky, kz)
    # k_grid = np.meshgrid(kx, ky, kz)

    # Norm of k
    k_norm =  cp.sqrt( kx_grid**2 + ky_grid**2 + kz_grid**2 ) # k = sqrt( kx^2 + ky^2  + kz^2 )
    k_norm[0][0] = cp.inf # Regularize divergence at k=0

    # Power Spectrum P_k
    power_spectrum = amplitude*(((2 * cp.pi/pixel)*k_norm)**(-1*k_power))  # P(k)=amplitude/k^{power},

    # Multiply the power spectrum with the transformed white noise to get the realization of the spectrum
    fourier_amplitudes_sqrt = cp.sqrt(power_spectrum)*fft_white_noise


    # Perform inverse Fourier transform to obtain the Gaussian random field in the spatial domain
    gaussian_random_field = cp.fft.ifftn(fourier_amplitudes_sqrt).real

    # Transfer the result back to CPU
    gaussian_random_field = cp.asnumpy(gaussian_random_field)

    return gaussian_random_field


def grf_3d(mean, std_dev, pixel, z_pixel, amplitude, k_power):
    # 3D Fast Fourier transform of the white noise
    white_noise = np.random.normal(mean, std_dev, (pixel, pixel, z_pixel))
    fft_white_noise = np.fft.fftn(white_noise)
    del white_noise
    gc.collect()

    # Generating FFT momentum
    kx = np.fft.fftfreq(pixel)*pixel
    ky = np.fft.fftfreq(pixel)*pixel
    kz = np.fft.fftfreq(z_pixel)*z_pixel

    # Genearting FFT momentum 3D array
    kx_grid, ky_grid, kz_grid = np.meshgrid(kx, ky, kz)
    del kx, ky, kz
    gc.collect()
    # k_grid = np.meshgrid(kx, ky, kz)

    # Norm of k
    k_norm =  np.sqrt( kx_grid**2 + ky_grid**2 + kz_grid**2 ) # k = sqrt( kx^2 + ky^2  + kz^2 )
    k_norm[0][0] = np.inf # Regularize divergence at k=0

    # Power Spectrum P_k
    power_spectrum = amplitude*(((2*np.pi/pixel)*k_norm)**(-1*k_power))  # P(k)=amplitude/k^{power},
    del k_norm  # Free memory
    gc.collect()

    # Multiply the power spectrum with the transformed white noise to get the realization of the spectrum
    fourier_amplitudes_sqrt = np.sqrt(power_spectrum, out=power_spectrum)*fft_white_noise
    del power_spectrum, fft_white_noise  # Free memory
    gc.collect()

    # Perform inverse Fourier transform to obtain the Gaussian random field in the spatial domain
    gaussian_random_field = np.fft.ifftn(fourier_amplitudes_sqrt).real
    del fourier_amplitudes_sqrt  # Free memory
    gc.collect()

    return gaussian_random_field

def gaussian_to_exp(x, lam):
    mu = np.mean(x)
    sigma = np.std(x)
    xu = 0.5 * (1 + erf((x - mu) / (np.sqrt(2) * sigma)))
    return -1/lam  * np.log(1 - xu)

# @title 1.3 Plots figures

def statistic_overview(exprf, n_sigma):

    all_points_3d = exprf.flatten()
    exprf_std_3d = np.std(all_points_3d)
    exprf_mean_3d = np.mean(all_points_3d)
    cutoff_3d = exprf_mean_3d + n_sigma*exprf_std_3d

    plt.style.use('seaborn-darkgrid')
    #print(f'Standard deviation = {exprf_std_3d:.2f}')
    #print(f'Mean = {exprf_mean_3d:.2f}')
    #print(f'Cutoff = {cutoff_3d:.2f}, i.e. {n_sigma} Sigmas from the mean at {exprf_mean_3d:.2f}')

    plt.hist(all_points_3d, bins=100);
    plt.yscale('log')
    plt.xlabel('Field amplitude', fontsize=12)
    plt.ylabel('Number of data points (Log)', fontsize=12)
    plt.axvline(x=cutoff_3d, color='r', linestyle='-', label='Cutoff amplitude')

    # Add text to the plot
    textstr = f'Std. Dev. = {exprf_std_3d:.2f}\nMean = {exprf_mean_3d:.2f}\nCutoff = {cutoff_3d:.2f} ({n_sigma} Std. Dev. from mean)'
    plt.text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10
            , verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.title('Random Field Statistics', fontsize=14)
    plt.legend(loc='upper right')
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    del all_points_3d
    gc.collect()
    # Save the plot with text
    plt.savefig('Statistic_info.pdf')
    plt.show()

    return cutoff_3d

"""# 2. **Main**"""

# @title Parameters
amplitude = 1 # amplitude of the power spectrum
k_power = 3 # power of k in the power spectrum

# Define the size of the square grid
pixel = 2**9  # 2^8 = 256
z_pixel = pixel # Reduce ram usage
#chunk_size = 2**8

# Parameters for the normal distribution
mean = 0      # Mean
std_dev = 1   # Standard deviation
# Parameters for exponential decay
decay_rate = 1
# Paratmer for cut-off
cutoff_sigma = 12
# 6-sigma of Gaussian(2*10E-9) ~ 18-sigmas of Exponential(5.6*10E-9)
# Using 12 Sigma for testing

"""## 2.2 3D Model"""

# @title Run 3D Model

# Run 3D Model (GPU)
#grf  = gpu_grf_3d(gaussian_white_noise_3d(pixel, z_pixel, mean, std_dev), pixel, z_pixel, amplitude, k_power)

## Work flow

# Run 3D Model (CPU)
grf =  grf_3d( mean, std_dev, pixel, z_pixel, amplitude, k_power)

# 1. Convert to exponential distribution
exprf = gaussian_to_exp(grf, decay_rate)

# 2. Delete Gaussiqn Field and summon trash can
del grf
gc.collect()

# 3. Save the exponential field to npy format
np.save('exponential_field.npy', exprf)

# 4. Save the field statistic to pdf format, return threshold values
cutoff_3d = statistic_overview(exprf, cutoff_sigma )

# 5. Save mask for positions where amplitude exceed threshold, delete exprf
mask = np.abs(exprf) > cutoff_3d
np.save('mask.npy', mask)

del exprf
gc.collect()

# 6. Save the positions where amplitude exceed threshold
positions = np.argwhere(mask)
np.save('mask_positions.npy', positions)