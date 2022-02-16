from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def mwa_freqspecs(input_spec, numchannels=24, separator=";"):
    """
    Validate the frequency specification given on the command line
    that can take the form of::

      <channel>
      <center>,<width>,<increment>
      <start>:<stop>:<increment>

    where the increments default to 1.  Multiple entries can be given separated by <separator>,
    which defaults to ;
    if using ;, entries should be enclosed in quotes

    :param input_spec: input string
    :param numchannels: number of frequency channels (int)
    :param separator: separator between the frequency channels (string)
    :return: list of frequency channels (ints)

    """
    freqs = []
    atoms = input_spec.split(separator)
    for atom in atoms:
        if not (":" in atom or "," in atom or "-" in atom):
            # just a number
            try:
                freqs.append(int(atom))
            except ValueError:
                raise ValidationError(
                    f"Unable to parse frequency channel: {atom}",
                    params={'input_spec': input_spec},
                )
        elif (":" in atom):
            sub_seperator = ":"
        elif ("-" in atom):
            sub_seperator = "-"
        elif ("," in atom):
            sub_seperator = ","

        # assumes <channelstart>:<channelstop>:<increment>
        increment = 1
        res = atom.split(sub_seperator)
        if (len(res) > 2):
            try:
                increment = int(res[2])
            except ValueError:
                raise ValidationError(
                    f"Unable to parse frequency increment: {res[2]}",
                    params={'input_spec': input_spec},
                )
        try:
            freqstart_center = int(res[0])
        except ValueError:
            raise ValidationError(
                f"Unable to parse frequency start: {res[0]}",
                params={'input_spec': input_spec},
            )
        try:
            freqstop_width = int(res[1])
        except ValueError:
            raise ValidationError(
                f"Unable to parse frequency stop: {res[1]}",
                params={'input_spec': input_spec},
            )
        if ":" in atom or "-" in atom:
            freqstart = freqstart_center
            freqstop = freqstop_width
            for freq in range(freqstart, freqstop + 1, increment):
                freqs.append(freq)
        else:
            freqcenter = freqstart_center
            freqwidth = freqstop_width
            for freq in range(freqcenter - int(freqwidth / 2.0), freqcenter + int(freqwidth / 2.0 + 0.5), increment):
                freqs.append(freq)

    # remove duplicates
    origfreqs = freqs
    freqs = list(set(freqs))
    if (len(freqs) < len(origfreqs)):
        raise ValidationError(
            f"Removed duplicate items from frequency list",
            params={'input_spec': input_spec},
        )
    # sort
    freqs.sort()
    # trim if necessary
    if len(freqs) > numchannels:
        raise ValidationError(
            f"Too many frequency channels supplied (>{numchannels}).",
            params={'input_spec': input_spec},
        )

    if (len(freqs) == 1):
        # only a single frequency
        logger.warning('--freq=%d requested, but interpreting it as --freq=%d,24' % (freqs[0], freqs[0]))
        freqcenter = freqs[0]
        freqwidth = 24
        increment = 1
        freqs = list(range(freqcenter - int(freqwidth / 2.0), freqcenter + int(freqwidth / 2.0 + 0.5), increment))

    if len(freqs) < numchannels:  # Pad to numchannels
        if freqs[-1] <= 255 - (24 - len(freqs)):
            freqs += list(range(freqs[-1] + 1, freqs[-1] + (24 - len(freqs)) + 1))
        elif freqs[0] > (24 - len(freqs)):
            freqs = list(range(freqs[0] - (24 - len(freqs)), freqs[0], 1)) + freqs
        else:
            freqs += [x for x in range(60, 200) if x not in freqs][:(24 - len(freqs))]
            freqs.sort()

    if (min(freqs) < 0) or (max(freqs) > 255):
        raise ValidationError(
            "Centre channel too close to 0 or 255, some channels would be < 0 or > 255",
            params={'input_spec': input_spec},
        )

    return freqs