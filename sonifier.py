import libaudioverse

modulator_start_frequency = 5
modulator_start_interval = 30
main_start_frequency = 130.8 # C3, 1 octave below Middle c.
main_volume = 0.3
semitone = 2**(1/12) # Multiplier for 1 semitone up or down.
semitone_range = 32 # We graph over 3 octaves.
# HRTF parameters.
hrtf_vertical_range = 0
hrtf_width = 180
block_size = 128
# HRTF only works well at 44100.
sr = 44100
block_duration = block_size/sr

def compute_frequencies(value, min_y, max_y):
    """Returns (modulator_frequency, modulator_interval, main) tuples.

This function does not error check. min_y < value < max_y, or else. Being silent outside the interval is the purpose of the class below."""
    normalized = (value-min_y)/(max_y-min_y)
    semitones = normalized*semitone_range
    multiplier = semitone**semitones
    modulator = modulator_start_frequency*multiplier
    modulator_interval = modulator_start_interval*multiplier
    main = main_start_frequency*multiplier
    return (modulator, modulator_interval, main)

class Sonifier:
    """Sonify a graph.

This class supports outputting to the sound card or a wave file. See __init__'s documentation for info on how to use it.

Every instance makes its own Libaudioverse server."""


    def __init__(self, f, duration, min_x, max_x, min_y, max_y, x_ticks = None, y_ticks = None, hrtf = False, axis_ticks = False):
        """Parameters:

f: A callable. Given a value for x, return a value for y.
duration: The total duration of the graph. We reach max_x at duration seconds, then stop.
min_x, max_x: The range of the X axis.
min_y, max_y: The range of the y axis.
x_ticks: If set to a value besides None, tick for every time we cross a multiple of the value.
y_ticks: x_ticks, but for y.
hrtf: If True, use HRTF panning.
axis_ticks: If True, tick for crossing x=0 or y=0.

x_ticks and y_ticks exist to allow representing graph lines through audio.
The visual equivalent of these values is the setting which allows one to specify the size of grid squares.
As this class graphs, it will produce distinct ticks as the value of f crosses multiples of x_ticks or y_ticks."""
        # This is around 3 milliseconds.  We can probably increase the resolution further.
        self.server = libaudioverse.Server(block_size = block_size, sample_rate = sr)
        self.main_tone = libaudioverse.AdditiveTriangleNode(self.server)
        self.main_modulator = libaudioverse.SineNode(self.server)
        self.main_modulator.connect(0, self.main_tone.frequency)
        self.main_modulator.mul = modulator_start_interval
        self.main_modulator.frequency = modulator_start_frequency
        self.main_tone.frequency = main_start_frequency
        self.main_tone.mul = main_volume
        self.panner = libaudioverse.MultipannerNode(self.server, "default")
        self.main_tone.connect(0, self.panner, 0)
        self.panner.connect(0, self.server)
        if hrtf:
            self.panner.strategy = libaudioverse.PanningStrategies.hrtf
        # These are for the small ticks. We don't necessaerily use them, but we get them going anyway so that we can if we want.
        self.x_ticker = libaudioverse.AdditiveSquareNode(self.server)
        self.y_ticker = libaudioverse.AdditiveSawNode(self.server)
        self.x_ticker.mul = 0
        self.y_ticker.mul = 0
        self.x_ticker.frequency = 300
        self.y_ticker.frequency = 400
        self.x_ticker.connect(0, self.panner, 0)
        self.y_ticker.connect(0, self.panner, 0)
        self.prev_x = min_x
        self.prev_y = f(min_x)
        self.server.set_block_callback(self.model_update)
        # We start not faded out.
        self.faded_out = False
        # Copy everything.
        self.f = f
        self.duration = duration
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self.hrtf = hrtf
        self.x_ticks = x_ticks
        self.y_ticks = y_ticks
        self.axis_ticks = axis_ticks
        self.finished = False

    def model_update(self, server, time):
        normalized_time = time/self.duration
        if normalized_time >= 1.0:
            # Schedule a fade out on the panner.
            self.panner.mul.linear_ramp_to_value(0.2, 0.0)
            self.server.set_block_callback(None)
            self.finished = True
        normalized_time = time/self.duration
        x_range = self.max_x-self.min_x
        x_offset = normalized_time*x_range
        x = self.min_x+x_offset
        y = self.f(x)
        if (y < self.min_y or y > self.max_y) and not self.faded_out:
            # Do a fast fade out.
            self.panner.mul.linear_ramp_to_value(block_duration/2, 0.0)
            self.faded_out = True
            return
        elif (y < self.min_y or y > self.max_y):
            # If we accidentally update the oscillators, they can get set to odd and very expensive values.
            return
        elif (self.min_y < y and y < self.max_y) and self.faded_out:
            self.panner.mul.linear_ramp_to_value(block_duration/2, 1.0)
            self.faded_out = False
        (modulator_freq, modulator_mul, main_freq) = compute_frequencies(y, self.min_y, self.max_y)
        #self.main_modulator.frequency = modulator_freq
        self.main_modulator.mul = modulator_mul
        self.main_tone.frequency = main_freq
        self.panner.azimuth = -(hrtf_width/2)+normalized_time*hrtf_width
        normalized_y = (y-self.min_y)/(self.max_y-self.min_y)
        normalized_y -= 0.5
        self.panner.elevation = hrtf_vertical_range*normalized_y
        # Ticks.
        if self.x_ticks:
            prev = self.prev_x//self.x_ticks
            now = x//self.x_ticks
            if now != prev:
                self.x_ticker.mul = 0.0
                self.x_ticker.reset()
                self.x_ticker.mul.linear_ramp_to_value(0.005, 0.5)
                self.x_ticker.mul.linear_ramp_to_value(0.05, 0.0)
        if self.y_ticks:
            prev = self.prev_y//self.y_ticks
            now = y//self.y_ticks
            if now != prev:
                self.y_ticker.mul = 0.0
                self.y_ticker.reset()
                self.y_ticker.mul.linear_ramp_to_value(0.005, 0.5)
                self.y_ticker.mul.linear_ramp_to_value(0.05, 0.0)
        self.prev_x = x
        self.prev_y = y

    def write_file(self, file):
        """Output to a file. .wav or .ogg."""
        self.server.write_file(path = file, channels = 2, duration = self.duration+0.5)

    def to_audio_device(self):
        self.server.set_output_device(channels = 2, mixahead = 10)

    def shutdown(self):
        self.server.clear_output_device()
        # the following is necessary to avoid a circular reference.
        self.server.set_block_callback(None)
