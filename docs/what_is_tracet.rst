TraceT
======

TraceT is the web-app for the Transient RApid-response using Coordinated Event Triggering (TRACE-T) project which is led by Gemma Anderson.
The web-app evolved out of two previous automated transient triggering projects, one on the Murchison Widefield Array (`MWA <https://www.mwatelescope.org/>`_), and one on the Australia Telescope Compact Array (`ATCA <https://www.narrabri.atnf.csiro.au/>`_).
The MWA triggering project is described in `Hancock et al, 2019 <https://ui.adsabs.harvard.edu/abs/2019PASA...36...46H/abstract>`_ and `Anderson et al, 2021 <https://ui.adsabs.harvard.edu/abs/2021PASA...38...26A/abstract>`_.

The triggering software monitors event streams, searching for alerts from detection instruments such as `Swift <https://swift.gsfc.nasa.gov/>`_, `Fermi <https://fermi.gsfc.nasa.gov/>`_, and `LIGO/Virgo/Kagra <https://gcn.nasa.gov/missions/lvk>`_, and then triggering followup observations on the `MWA <https://www.mwatelescope.org/>`_ or `ATCA <https://www.narrabri.atnf.csiro.au/>`_.
The events are received as `VOevents <https://voevent.readthedocs.io/en/latest/>`_ from a `VOevent broker network <https://4pisky.org/voevents/>`_ or via a Kafka stream (`GCN <https://gcn.nasa.gov/>`_).

`This software <https://github.com/ADACS-Australia/TraceT>`_ has been updated and adapted from the `original <https://github.com/MWATelescope/mwa_trigger>`_ thanks to the work of Astronomy Data And Computing Services (`ADACS <https://adacs.org.au/>`_).