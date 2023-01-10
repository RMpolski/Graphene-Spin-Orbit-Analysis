import numpy as np
import lmfit
from lmfit import Parameters, Minimizer
from scipy.special import digamma
import pandas as pd


#### Set up to run with Minimizer

data = np.loadtxt('./Data_array.txt')
Btot, Gtot = data[0, :], data[1, :]

hbar = 6.626e-34/(2*np.pi)
esqh = 1.602e-19**2/6.626e-34*1000

def F(z):
    return np.log(z) + digamma(0.5 + 1/z)

def dsigma_WAL(B, tau_phi, tau_asy, tau_sym, vF):
    """Defines the spin-orbit coupling fit equation. 
    Args: 
    B: magnetic field in mT, 
    tau_phi: T-dependent scattering time in ps
    tau_asy: asymmetric spin-orbit coupling scattering time in ps
    tau_sym: using the symmetric spin-orbit coupling instead of total so that the value
             isn't quite as constrained (it can be > or < tau_asy)
    
    Note they've been scaled appropriately below. Scaled params are appended with an 's'
    to avoid namespace issues.
    
    Returns: The theoretical change in conductivity from B=0, in units of e^2/h 
    (which has to be converted from mS)
    """
    
    tau = 15982e-4*hbar*np.sqrt(np.pi*0.69021e16)/(1.602e-19*vF)
    D = 0.5*vF**2*tau
    B_s = B/1000
    tau_phi_s = tau_phi*1e-12
    tau_asy_s = tau_asy*1e-12
    tau_sym_s = tau_sym*1e-12
    tau_so_s = (tau_asy_s**(-1) + tau_sym_s**(-1))**(-1)
    tau_binv = 4*D*1.602e-19*B_s/(6.626e-34/(2*np.pi))
    return -1.602e-19**2/(2*np.pi*6.626e-34)/esqh*1000*(F(tau_binv/(tau_phi_s**-1)) \
                                                        - F(tau_binv/(tau_phi_s**-1 + 2*tau_asy_s**-1)) \
                                                        - 2*F(tau_binv/(tau_phi_s**-1 + tau_so_s**-1)))


def residuals(params, B, data):
    p = params.valuesdict()
    vF = p['vF']
    tauphi_1, tauphi_2, tauphi_3, tauphi_4 = p['tauphi_1'], p['tauphi_2'], p['tauphi_3'], p['tauphi_4']
    tau_asy = p['tau_asy']
    tau_sym = p['tau_sym']
    
    nB = int(len(B)/4)  # divide the magnetic field into 4 sections, one for each model
    dsigma1 = dsigma_WAL(B[:nB], tauphi_1, tau_asy, tau_sym, vF)
    dsigma2 = dsigma_WAL(B[nB:2*nB], tauphi_2, tau_asy, tau_sym, vF)
    dsigma3 = dsigma_WAL(B[2*nB:3*nB], tauphi_3, tau_asy, tau_sym, vF)
    dsigma4 = dsigma_WAL(B[3*nB:], tauphi_4, tau_asy, tau_sym, vF)
    
    ## direct residuals: gives 
    dsigma = np.concatenate((dsigma1, dsigma2, dsigma3, dsigma4))
    return (dsigma - data)  # the function squares it for us, so we can leave it like this


def run_Minimizer(vF_tauphi_list):
    results_tau_asy = []
    results_tau_asy_stderr = []
    results_tau_sym = []
    results_tau_sym_stderr = []
    chisq = []
    vF_vals = []
    tauphi_1_vals = []
    
    for idx, vals in enumerate(vF_tauphi_list):
        vF_set, tauphi_1_set = vals
        vF_vals.append(vF_set)
        tauphi_1_vals.append(tauphi_1_set)

        params = Parameters()
        params.add('vF', value=vF_set, vary=False)
        params.add('tauphi_1', value=tauphi_1_set, vary=False)
        params.add('tauphi_2', value=28, min=0.01, max=80)
        params.add('tauphi_3', value=12, min=0.01, max=80)
        params.add('tauphi_4', value=6, min=0.01, max=80)
        params.add('tau_asy', value=7, min=0.01, max=100)
        params.add('tau_sym', value=1, min=0.01, max=100)

        mini = Minimizer(residuals, params, fcn_args=(Btot, Gtot))
        out1 = mini.minimize(method='basinhopping', T=0.05, stepsize=0.01)
        out2 = mini.minimize(method='leastsq', params=out1.params)
        
        results_tau_asy.append(out2.params['tau_asy'].value)
        results_tau_asy_stderr.append(out2.params['tau_asy'].stderr)
        results_tau_sym.append(out2.params['tau_sym'].value)
        results_tau_sym_stderr.append(out2.params['tau_sym'].stderr)
        chisq.append(out2.chisqr)
        
    df = pd.DataFrame()
    df['vF'] = vF_vals
    df['tauphi_1'] = tauphi_1_vals
    df['tau_asy'] = results_tau_asy
    df['tau_asy_std'] = results_tau_asy_stderr
    df['tau_sym'] = results_tau_sym
    df['tau_sym_std'] = results_tau_sym_stderr
    df['chisquare'] = chisq
    
    return df
    