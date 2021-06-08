#!/usr/bin/env python3

# Spiderweb/radar/radial chart in plotly, adapted from
# https://towardsdatascience.com/how-to-make-stunning-radar-charts-with-python-implemented-in-matplotlib-and-plotly-91e21801d8ca
# See also https://plotly.com/python/radar-chart/

import plotly.graph_objects as go
import plotly.offline as pyo


categories = ['Food Quality', 'Food Variety', 'Service Quality',
              'Ambience', 'Affordability']
categories = [*categories, categories[0]]

restaurants = {
    'India Palace':  [4, 4, 5, 4, 3],
    'Taco Paradise': [5, 5, 4, 5, 2],
    'Greasy Spoon and Fork': [3, 4, 5, 3, 5]
}
data = []

for rest in restaurants:
    # the last point must be a duplicate of the first
    data.append(go.Scatterpolar(r=restaurants[rest]+[restaurants[rest][0]],
                                theta=categories,
                                fill='toself',
                                name=rest))

fig = go.Figure(data=data,
    layout=go.Layout(
        title=go.layout.Title(text='Restaurant comparison'),
        polar={'radialaxis': {'visible': True}},
        showlegend=True
    )
)

pyo.plot(fig)
print("Go look at your browser window")
