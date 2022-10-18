# Materials for 231.028 Methods and Models, 2022W

### Notebooks
* [descriptive_statistics.ipynb](descriptive_statistics.ipynb): processes GTFS data and generates the trajectory plots for service runs of Wiener Lienen.
* [transit_sim.py](transit_sim.py): snippets from the open-sourced transit simulation program [transit_sim](https://github.com/cb-cities/transit_sim) to assist data cleaning.
* [discrete_choice.ipynb](discrete_choice.ipynb): runs a simple random utility model for three route options between Längenfeldgasse to Stephansplatz.
* [regression.ipynb](regression.ipynb): performs nonlinear regression on transformed vehicle energy use dataset.

If you don't have Python installed, you can run the above notebook using Google Colab by clicking on the buttons below. You will need a Google account to do this.
[![descriptive statistics](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bz247_course_materials/blob/master/methods_and_models_2022W/descriptive_statistics.ipynb)
[![discrete choice](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bz247_course_materials/blob/master/methods_and_models_2022W/discrete_choice.ipynb)
[![regression](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/bz247_course_materials/blob/master/methods_and_models_2022W/regression.ipynb)


### Data
Data needed for the notebooks can be downloaded from https://tuwienacat-my.sharepoint.com/:u:/g/personal/bingyu_zhao_tuwien_ac_at/EbSDlN7P2YZKtvbbjyGNHJwBGAqtGRTWbgA3oFfx_bJL5A?e=5JAaRA

Data sources:
1. regression_emission_data: raw data are from Oh et al. (2022). Vehicle Energy Dataset https://github.com/gsoh/VED, or see the paper at https://ieeexplore.ieee.org/document/9262035/. 
2. vienna_gtfs: raw data are from https://www.transit.land/feeds/f-u2ed-wienerlinien~wlb/ 

Both datasets have been heavily processed and interested readers should refer to the original datasets.