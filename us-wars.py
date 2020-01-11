#!/usr/bin/env python3

import datetime

# Source: https://www.thoughtco.com/american-involvement-wars-colonial-times-present-4059761
wars = [
    [ "1675-1676", "King Philip's War", "New England Colonies vs. Wampanoag, Narragansett, and Nipmuck Indians" ],
    [ "1689-1697", "King William's War", "The English Colonies vs. France" ],
    [ "1702-1713", "Queen Anne's War (War of Spanish Succession)", "The English Colonies vs. France" ],
    [ "1744-1748", "King George's War (War of Austrian Succession)", "The French Colonies vs. Great Britain" ],
    [ "1756-1763", "French and Indian War(Seven Years War)", "The French Colonies vs. Great Britain" ],
    [ "1759-1761", "Cherokee War", "English Colonists vs. Cherokee Indians" ],
    [ "1775-1783", "American Revolution", "English Colonists vs. Great Britain" ],
    [ "1798-1800", "Franco-American Naval War", "United States vs. France" ],
    [ "1801-1805", "Barbary Wars", "United States vs. Morocco, Algiers, Tunis, and Tripoli" ],
    [ "1815", "Barbary Wars", "United States vs. Morocco, Algiers, Tunis, and Tripoli" ],
    [ "1812-1815", "War of 1812", "United States vs. Great Britain" ],
    [ "1813-1814", "Creek War", "United States vs. Creek Indians" ],
    [ "1836", "War of Texas Independence", "Texas vs. Mexico" ],
    [ "1846-1848", "Mexican-American War", "United States vs. Mexico" ],
    [ "1861-1865", "U.S. Civil War", "Union vs. Confederacy" ],
    [ "1898", "Spanish-American War", "United States vs. Spain" ],
    [ "1914-1918", "World War I", "Triple Alliance: Germany, Italy, and Austria-Hungary vs. Triple Entente: Britain, France, and Russia. The United States joined on the side of the Triple Entente in 1917." ],
    [ "1939-1945", "World War II", "Axis Powers: Germany, Italy, Japan vs. Major Allied Powers: United States, Great Britain, France, and Russia" ],
    [ "1950-1953", "Korean War", "United States (as part of the United Nations) and South Korea vs. North Korea and Communist China" ],
    [ "1960-1975", "Vietnam War", "United States and South Vietnam vs. North Vietnam" ],
    [ "1961", "Bay of Pigs Invasion", "United States vs. Cuba" ],
    [ "1983", "Grenada", "United States Intervention" ],
    [ "1989", "US Invasion of Panama", "United States vs. Panama" ],
    [ "1990-1991", "Persian Gulf War", "United States and Coalition Forces vs. Iraq" ],
    [ "1995-1996", "Intervention in Bosnia and Herzegovina", "United States as part of NATO acted peacekeepers in former Yugoslavia" ],
    [ "2001-present", "Invasion of Afghanistan", "United States and Coalition Forces vs. the Taliban regime in Afghanistan to fight terrorism." ],
    [ "2003-2011", "Invasion of Iraq", "United States and Coalition Forces vs. Iraq" ],
    [ "2004-present", "War in Northwest Pakistan", "United States vs. Pakstan, mainly drone attacks" ],
    [ "2007-present", "Somalia and Northeastern Kenya", "United States and Coalition forces vs. al-Shabaab militants" ],
    [ "2009-2016", "Operation Ocean Shield (Indian Ocean)", "NATO allies vs. Somali pirates" ],
    [ "2011", "Intervention in Libya", "US and NATO allies vs. Libya" ],
    [ "2011-2017", "Lord's Resistance Army", "US and allies against the Lord's Resistance Army in Uganda" ],
    [ "2014-2017", "US-led Intervention in Iraq", "US and coalition forces against the Islamic State of Iraq and Syria" ],
    [ "2014-present", "US-led intervention in Syria", "US and coalition forces against al-Qaeda, Isis, and Syria" ],
    [ "2015-present", "Yemeni Civil War", "Saudi-led coalition and US, France and Kingdom against the Houthi rebels, Supreme Political Council in Yemen and allies" ],
    [ "2015-present", "US intervention in Libya", "US and Libya against ISIS" ]
]


def gantt_plotly(plotdata, title):
    import plotly.figure_factory as ff

    fig = ff.create_gantt(plotdata, width=1024, height=800, title=title)
    fig.show()
    # outfile = "us-wars.jpg"
    # fig.write_image(outfile)
    # print("wrote", outfile)


def gantt_matplotlib(plotdata, title):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(len(plotdata)/2, len(plotdata) / 4))

    from itertools import cycle

    # Create a colour code cycler e.g. 'C0', 'C1', etc.
    color_codes = map('C{}'.format, cycle(range(10)))

    THICKNESS = 3
    VSPACE = THICKNESS + 1
    TOP = 1000

    y = TOP
    ytics = []
    yticlabels = []
    for p in plotdata:

        color = next(color_codes)

        y -= VSPACE
        ax.broken_barh([(p['startyear'], p['endyear'] - p['startyear'])],
                       (y-THICKNESS, THICKNESS),
                       facecolor=color, label=p['Task'])
        ytics.append(y-THICKNESS/2)
        yticlabels.append(p['Task'])

    ax.set_yticks(ytics)
    ax.set_yticklabels(yticlabels)

    ax.set_title(title)

    ax.grid(True)

    # ax.annotate('arrow', (61, 25),
    #             xytext=(0.8, 0.9), textcoords='axes fraction',
    #             arrowprops=dict(facecolor='black', shrink=0.05),
    #             fontsize=16,
    #             horizontalalignment='right', verticalalignment='top')

    plt.tight_layout()

    plt.savefig("us-wars.jpg")
    plt.show()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        try:
            yearsfrom = int(sys.argv[1])
        except:
            import os
            print(f"Usage: {os.path.basename(sys.argv[0])} [startyear]")
            sys.exit(1)
    else:
        yearsfrom = None

    plotdata = []
    for war in wars:
        years = war[0].split('-')
        if len(years) == 2:
            startyear = int(years[0])
            if years[1] == 'present':
                endyear = datetime.date.today().year
            else:
                endyear = int(years[1])
        else:
            startyear = int(war[0])
            endyear = startyear+1

        # Comment this out to show all wars, not just modern ones.
        if yearsfrom and endyear < yearsfrom:
            continue

        plotdata.append(dict(Task=war[1],
                             startyear=startyear, endyear=endyear,
                             # Start and Finish are for plotly's gantt
                             Start=f'{startyear}-01-01',
                             Finish=f'{endyear}-02-28'))

    if plotdata[0]['startyear'] < 1900:
        title = "US Wars since 1675"
    else:
        title = "US Wars since 1900"
    gantt_matplotlib(plotdata, title)
