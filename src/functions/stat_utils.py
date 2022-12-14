# %% Dependencies imports
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator, NullLocator
from matplotlib.dates import YearLocator

# %% Typing imports
import numpy.typing as npt
from typing import Sequence
from matplotlib.figure import Figure

# %% Functions
def na_seadec(
    x: pd.Series, method: str = "linear", model: str = "additive"
) -> pd.Series:
    """
    Function to interpolate the NaN values in a series but without affect
    the long term trend and the seasonal component.

    This function decompose the time series and interpolate the anomalies with
    the interpolation method selectd by he user.

    This function was made based on ImputeTS function for R with the same
    name: https://github.com/SteffenMoritz/imputeTS/

    Parameters
    ----------
    x : pd.Series
        Series of interest with the NaN values.

    method : str
        Method of interpolation to fill the NaN values in the anomalies.
        the full list of option coul be found in pandas.Series.interpolate()
        method:
        https://pandas.pydata.org/docs/reference/api/pandas.Series.interpolate.html

    model : str
        Additive or Multiplicative. The kind of model to decompose the
        time series. To read more about the difference between the two models
        could be found in statsmodels.tsa.seasonal.seasonal_decompose()
        function documentation:
        https://www.statsmodels.org/dev/generated/statsmodels.tsa.seasonal.seasonal_decompose.html

    Returns
    -------
    x : pd.Series
        Series interpolated.
    """

    # Get the time to reconstruct the series
    time = x.index

    # Find the NaN values
    mask = x.isna()

    # Interpolate the original series
    interpolated = x.interpolate(method=method)

    # Decompose the series with seasonal_decompose from statsmodels
    components = seasonal_decompose(interpolated, model=model, extrapolate_trend="freq")

    # Sum the trend with the residuals to get the series without
    # seasonality
    if model == "additive":
        ts_no_seasonal = components.trend + components.resid
    else:
        ts_no_seasonal = components.trend / components.resid

    # Restor the NaN values
    ts_no_seasonal[mask] = np.nan

    # Create the second series to interpolate data without seasonality
    x2 = pd.Series(data=ts_no_seasonal, index=time)

    # Interpolate TS without seasonality
    x2 = x2.interpolate(method=method)

    # Add the seasonality to the interpolated data
    if model == "additive":
        x2 = x2 + components.seasonal
    else:
        x2 = x2 / components.seasonal

    # Fill the NaN with the interpolated data
    x[mask] = x2[mask]

    return x


def detrend_variables(
    data: pd.DataFrame, variables: npt.ArrayLike | None = None
) -> pd.DataFrame:
    """
    Function to detrend de variables of a dataframe.

    Parameters
    ----------
    data : pd.DataFrame
        Dataframe with the variables to detrend.

    variables : ArrayLike | None = None
        Variables of interest.

    Returns
    -------
    dat2 : pd.DataFrame
        Dataframes with the variables detrended.

    """
    # Create a copy of the original dataframe
    dat2 = data.copy()

    # If variables is not defined, take all variables in the dataframe
    if variables == None:
        variablles = data.columns

    # Iterate throught variables
    for variable in variables:
        # Decompose the variable
        components = seasonal_decompose(dat2[variable], extrapolate_trend="freq")

        # Save the detrended data in the second dataframe
        dat2[variable] = components.observed - components.trend

    return dat2


def corr_matrix(
    data: pd.DataFrame,
    variables: npt.ArrayLike | None = None,
    half: bool = False,
    hide_insignificants: bool = False,
    singificant_threshold: float = 0.05,
) -> pd.DataFrame:
    """
    Calculate the pearson correlation matrix of the variables in a dataframe.

    Parameters
    ----------
    data : pd.DataFrame
        Dataframe with the variables to evaluate their correlation.

    variables : ArrayLike | None = None
        The variables of interest, if it is not defined, all variables in
        the dataframe will be evaluated.

    half : bool = False
        If True, only show the corerlation of the first half of the matrix,
        excluding the repeated correlation.

    hide_insignifcants : bool = False
        If True, hide all the correlation with a p-value greater than the
        significant threshold.

    siginificant_threshold : float = 0.05
        Threshold of significant correlation.

    returns
    -------
    corr : pd.DataFrame
        Dataframe with the correlation values.

    """
    if variables == None:
        variables = data.columns

    reverse = variables[::-1]

    N = len(variables)

    corr = np.empty((N, N))
    pval = np.full((N, N), np.nan)
    mask = np.full((N, N), np.nan)

    for i, iv in enumerate(variables):
        for j, jv in enumerate(reverse):
            c, p = pearsonr(data[iv], data[jv])
            corr[j, i] = c

            if p <= singificant_threshold:
                pval[j, i] = 1.0

        mask[: N - i, i] = 1.0

    if half:
        corr *= mask

    if hide_insignificants:
        corr *= pval

    corr = pd.DataFrame(data=corr, index=reverse, columns=variables)

    return corr


def plot_ts_components(
    data: pd.DataFrame,
    figsize: Sequence[float] = (7, 4),
    ENSO: npt.ArrayLike | None = None,
    ENSO_keys: Sequence = ["Nina", "Nino"],
    ENSO_scale: float = 0.05,
    titles: dict[str, str] | None = None,
) -> Figure:
    """
    Function to plot the time series components of all variables in a dataframe.

    Parameters
    ----------
    data : pandas.DataFrame
        Dataframe with the variables and time at index

    figsize : Sequence[width, height]
        Size of the figure.

    ENSO : numpy.ndarray | None = None
        Array use to plot ENSO phases stripes on time series.

    ENSO_keys : Sequence = ["Nina", "Nino"]
        ENSO Keys for La Ni??a ENSO cold phase and EL Ni??o ENSO warm phase,
        respectively.

    ENSO_scale : float = 0.05
        Scale to plot the stripes.

    titles : dict[str, str] | None = None
        Custom titles for the time series.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure with the TS components.

    """
    # Dictionary to store decomposed dataframes
    decomposed_data = {}

    # For all variabels in the dataframe extract all the TS components
    # and save it in the dictinary
    for variable in data.columns:
        try:
            components = seasonal_decompose(data[variable], extrapolate_trend="freq")
        except:
            continue

        decomposed_data[variable] = pd.DataFrame(
            {
                "Observed": components.observed,
                "Trend": components.trend,
                "Detrended": components.observed - components.trend,
                "Seasonal": components.seasonal,
                "Anomalies": components.resid,
            }
        )

    # Get the variables to iterate them
    variables = [k for k in decomposed_data.keys()]

    # Create the figure and the axes
    fig, axs = plt.subplots(figsize=figsize, nrows=5, ncols=len(variables), sharex=True)

    # Iterate trought variables to plot them by column
    for i, variable in enumerate(variables):
        # Get the components
        components = decomposed_data[variable].columns

        # Iterate the components to plot the by row
        for j, component in enumerate(components):
            x = decomposed_data[variable].index
            y = decomposed_data[variable][component]

            # Plot ENSO Stripes if ENSO is an array
            try:
                ENSO.any()
            except:
                continue
            else:
                # Plot La Ni??a ENSO Phase stripes
                axs[j, i].fill_between(
                    x,
                    np.min(y) - ENSO_scale * np.max(y),
                    np.max(y) + ENSO_scale * np.max(y),
                    where=ENSO == ENSO_keys[0],
                    color="blue",
                    alpha=0.2,
                )

                # Plot El Ni??o ENSO Phase stripes
                axs[j, i].fill_between(
                    x,
                    np.min(y) - ENSO_scale * np.max(y),
                    np.max(y) + ENSO_scale * np.max(y),
                    where=ENSO == ENSO_keys[1],
                    color="red",
                    alpha=0.2,
                )

            # Plot data
            axs[j, i].plot(x, y, color="black", lw=0.5)

            # In the first row add the variable title
            if j == 0:
                if titles != None:
                    axs[j, i].set_title(titles[variable], fontsize=8)
                else:
                    axs[j, i].set_title(variable, fontsize=8)

            # In the first column add the component in the label
            if i == 0:
                axs[j, i].set_ylabel(component)

            # In the last row add the time label
            if j == 4:
                axs[j, i].set_xlabel("Time [Y]")

            # Set the x-ticks to multiples of 5 years and the minor ticks to 1 year
            axs[j, i].xaxis.set_major_locator(YearLocator(5))
            axs[j, i].xaxis.set_minor_locator(YearLocator(1))

    # Align all the y-labels in the first column
    fig.align_ylabels(axs[:, 0])

    return fig


def plot_acf_ccf(
    data: dict[str, npt.ArrayLike],
    ci: float,
    ylims: Sequence[float] = [-1, 1],
    titles: dict[str, str] | None = None,
) -> Figure:
    """
    Function to plot ACF and CCF data previously calculated.

    Paramters
    ---------
    data : dict[str, numpy.ndarray]
        Dictinary with autocorrelation or cross-correlation data

    ci : float
        Confidence interval of correlation.

    ylims :  Sequence[bottom, top] = [-1, 1]
        Limits of correlation for the plot.

    titles : dict[str, str] | None = None
        Custom titles for the plots.

    Returns
    -------
    fig : matplotlib.figure.Figure
        Figure with the correlations plots.

    """
    # Get the correlation tests from the data
    tests = [t for t in data.keys()]
    # Get how many there are to define the figure dimensions
    n = len(tests)

    # Show error if ylims is list don't have two elements
    if len(ylims) != 2:
        Exception("ylims must have lenght of 2")

    # Create the figure and GridSpec for axes
    fig = plt.figure()
    grs = GridSpec(nrows=2, ncols=2, figure=fig)

    # Define the figures axes based on n, where n more than 4 show error
    match n:
        case 1:
            axs = [fig.add_subplot(grs[:, :])]
            axs[0].set(xlabel="Lags [months]", ylabel="Correlation")
        case 2:
            axs = [fig.add_subplot(grs[0, :]), fig.add_subplot(grs[1, :])]
            axs[0].set(ylabel="Correlation")
            axs[1].set(xlabel="Lags [months]", ylabel="Correlation")
        case 3:
            axs = [
                fig.add_subplot(grs[0, 0]),
                fig.add_subplot(grs[1, :]),
                fig.add_subplot(grs[0, 1]),
            ]
            axs[0].set(ylabel="Correlation")
            axs[1].set(xlabel="Lags [months]", ylabel="Correlation")

        case 4:
            axs = [
                fig.add_subplot(grs[0, 0]),
                fig.add_subplot(grs[1, 0]),
                fig.add_subplot(grs[0, 1]),
                fig.add_subplot(grs[1, 1]),
            ]
            axs[0].set(ylabel="Correlation")
            axs[1].set(xlabel="Lags [months]", ylabel="Correlation")
            axs[3].set(xlabel="Lags [months]")

        case _:
            Exception("data must have a lenght lower or equal than 4")

    # For loop to plot ACF o CCF by variable
    for i, (test, ax) in enumerate(zip(tests, axs)):
        # Plot correlation data as stem
        ax.stem(data[test], basefmt=" ", markerfmt=" ")

        # Add a line at 0 and the confidence intervals
        ax.axhline(0, color="black")
        ax.axhline(ci, color="black", linestyle="--")
        ax.axhline(-ci, color="black", linestyle="--")

        # If there are custon titles add them to the plot, else
        # use the  default titles
        if titles != None:
            ax.set_title(titles[test], fontsize=8)
        else:
            ax.set_title(test, fontsize=8)

        # Set ylims and ticks
        ax.set_ylim(bottom=ylims[0], top=ylims[1])
        ax.xaxis.set_major_locator(MultipleLocator(4))
        ax.xaxis.set_minor_locator(MultipleLocator(1))

    # Share all x and y axis
    axs[0].get_shared_x_axes().join(*axs)
    axs[0].get_shared_y_axes().join(*axs)

    return fig


def plot_corr_matrix(
    data: pd.DataFrame,
    variables: npt.ArrayLike | None = None,
    half: bool = False,
    hide_insignificants: bool = False,
    singificant_threshold: float = 0.05,
    show_labels: bool = True,
    show_colorbar: bool = False,
    palette: str = "Spectral",
    text_color: str = "black",
) -> Figure:
    """
    Calculate the pearson correlation matrix of the variables in a dataframe.

    Parameters
    ----------
    data : pd.DataFrame
        Dataframe with the variables to evaluate their correlation.

    variables : ArrayLike | None = None
        The variables of interest, if it is not defined, all variables in
        the dataframe will be evaluated.

    half : bool = False
        If True, only show the corerlation of the first half of the matrix,
        excluding the repeated correlation.

    hide_insignifcants : bool = False
        If True, hide all the correlation with a p-value greater than the
        significant threshold.

    siginificant_threshold : float = 0.05
        Threshold of significant correlation.

    show_labels : bool = True
        Show the correlation value.

    show_colorbar : bool = False
        Show colorbar.

    palette : str = Spectral
        Color palette for correlation plot.

    text_color : str = black
        Color of text correlation labels.

    returns
    -------
    corr : pd.DataFrame
        Dataframe with the correlation values.

    """

    # If variables are not defined get all columns from data
    if variables == None:
        variables = data.columns

    # Get the number of variables
    N = len(variables)

    # Reverse variables for plot
    reverse = variables[::-1]

    # Get the correlation matrix
    corr = corr_matrix(
        data, variables, half, hide_insignificants, singificant_threshold
    )

    if show_colorbar:
        fs = (4, 3)
    else:
        fs = (3, 3)

    # Create the figure and the axes
    fig = plt.figure(figsize=fs)
    ax1 = plt.subplot(1, 1, 1)

    # Plot matrix with pcolormesh
    im1 = ax1.pcolormesh(
        variables, reverse, corr, cmap=palette, edgecolor="w", vmin=-1, vmax=1
    )

    # Invert y axis
    ax1.invert_yaxis()

    # Add the colorbar
    if show_colorbar:
        cax = ax1.inset_axes([1.04, 0.1, 0.05, 0.8])
        bar = plt.colorbar(im1, cax=cax, label="Correlation")

    if show_labels:
        x, y = np.meshgrid(np.arange(N), np.arange(N))
        x = x.reshape(-1)
        y = y.reshape(-1)
        t = corr.values.reshape(-1)

        for xi, yi, ti in zip(x, y, t):
            if np.isfinite(ti):
                ax1.text(
                    xi,
                    yi,
                    round(ti, 2),
                    color=text_color,
                    size=8,
                    ha="center",
                    va="center",
                )

    # Rotate labels to improve their readability
    ax1.set_xticklabels(variables, rotation=30)
    ax1.xaxis.set_minor_locator(NullLocator())
    ax1.yaxis.set_minor_locator(NullLocator())

    return fig
