import libaudioverse

main_start_frequency = 130.8 # C3, 1 octave below Middle c.
main_volume = 0.3
semitone = 2**(1/12) # Multiplier for 1 semitone up or down.
semitone_range = 32 # We graph over 3 octaves.
# HRTF parameters.
hrtf_width = 1
hrtf_height = 1
hrtf_listener_offset = 0.2
block_size = 128
# HRTF only works well at 44100.
sr = 44100
block_duration = block_size/sr

def compute_frequencies(value, min_y, max_y):
    """Returns the frequency of the tone.

This function does not error check. min_y < value < max_y, or else. Being silent outside the interval is the purpose of the class below."""
    normalized = (value-min_y)/(max_y-min_y)
    semitones = normalized*semitone_range
    multiplier = semitone**semitones
    return main_start_frequency*multiplier

class Sonifier:
    """Sonify a graph.

This class supports outputting to the sound card or a wave file. See __init__'s documentation for info on how to use it.

Every instance makes its own Libaudioverse server."""


    def __init__(self, f, duration, min_x, max_x, min_y, max_y, x_ticks = None, y_ticks = None, zero_ticks = False, hrtf = False, axis_ticks = False):
        """Parameters:

f: A callable. Given a value for x, return a value for y.
duration: The total duration of the graph. We reach max_x at duration seconds, then stop.
min_x, max_x: The range of the X axis.
min_y, max_y: The range of the y axis.
x_ticks: If set to a value besides None, tick for every time we cross a multiple of the value.
y_ticks: x_ticks, but for y.
zero_ticks: tick when y crosses zero.
hrtf: If True, use HRTF panning.
axis_ticks: If True, tick for crossing x=0 or y=0.

x_ticks and y_ticks exist to allow representing graph lines through audio.
The visual equivalent of these values is the setting which allows one to specify the size of grid squares.
As this class graphs, it will produce distinct ticks as the value of f crosses multiples of x_ticks or y_ticks."""
        # This is around 3 milliseconds.  We can probably increase the resolution further.
        self.server = libaudioverse.Server(block_size = block_size, sample_rate = sr)
        self.main_tone = libaudioverse.AdditiveTriangleNode(self.server)
        self.main_tone.frequency = main_start_frequency
        self.main_tone.mul = main_volume
        # This helps HRTF a little.
        self.main_noise = libaudioverse.NoiseNode(self.server)
        self.main_noise.mul = 0.01
        self.panner = libaudioverse.MultipannerNode(self.server, "default")
        self.environment = libaudioverse.EnvironmentNode(self.server, "default")
        self.source = libaudioverse.SourceNode(self.server, self.environment)
        self.main_tone.connect(0, self.panner, 0)
        self.main_tone.connect(0, self.source, 0)
        if hrtf:
            self.main_noise.connect(0, self.panner, 0)
            self.environment.connect(0, self.server)
            self.environment.panning_strategy = libaudioverse.PanningStrategies.hrtf
            self.environment.position = (0, 0, hrtf_listener_offset)
        else:
            self.panner.connect(0, self.server)
        # These are for the small ticks. We don't necessarily use them, but we get them going anyway so that we can if we want.
        self.x_ticker = libaudioverse.AdditiveSquareNode(self.server)
        self.y_ticker = libaudioverse.AdditiveSawNode(self.server)
        self.zero_ticker = libaudioverse.AdditiveSawNode(self.server)
        self.x_ticker.mul = 0
        self.y_ticker.mul = 0
        self.zero_ticker.mul = 0
        self.x_ticker.frequency = 115
        self.x_ticker.connect(0, self.panner, 0)
        self.y_ticker.connect(0, self.panner, 0)
        self.zero_ticker.connect(0, self.panner, 0)
        self.prev_x = min_x
        self.prev_y = f(min_x)
        if f(min_x) < 0: self.prev_y_sign = -1
        elif f(min_x) == 0: self.prev_y_sign = 0
        else: self.prev_y_sign = 1
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
        self.zero_ticks = zero_ticks
        self.axis_ticks = axis_ticks
        self.finished = False

    def model_update(self, server, time):
        if self.hrtf:
            fade_target = self.environment
        else:
            fade_target = self.panner
        normalized_time = time/self.duration
        if normalized_time >= 1.0:
            # Schedule a fade out on the panner.
            fade_target.mul.linear_ramp_to_value(0.2, 0.0)
            self.server.set_block_callback(None)
            self.finished = True
        normalized_time = time/self.duration
        x_range = self.max_x-self.min_x
        x_offset = normalized_time*x_range
        x = self.min_x+x_offset
        y = self.f(x)
        if (y < self.min_y or y > self.max_y) and not self.faded_out:
            # Do a fast fade out.
            fade_target.mul.linear_ramp_to_value(block_duration/2, 0.0)
            self.faded_out = True
            return
        elif (y < self.min_y or y > self.max_y):
            # If we accidentally update the oscillators, they can get set to odd and very expensive values.
            return
        elif (self.min_y < y and y < self.max_y) and self.faded_out:
            fade_target.mul.linear_ramp_to_value(block_duration/2, 1.0)
            self.faded_out = False
        main_freq = compute_frequencies(y, self.min_y, self.max_y)
        self.main_tone.frequency = main_freq
        self.panner.azimuth = -(180/2)+normalized_time*180
        normalized_y = (y-self.min_y)/(self.max_y-self.min_y)
        self.source.position = (normalized_time-0.5, normalized_y-0.5, 0)
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
                self.y_ticker.frequency = main_freq
                self.y_ticker.mul.linear_ramp_to_value(0.005, 0.5)
                self.y_ticker.mul.linear_ramp_to_value(0.05, 0.0)
        if y < 0: y_sign = -1
        elif y == 0: y_sign = 0
        else: y_sign = 1
        if self.zero_ticks:
            if ((self.prev_y_sign != 0 and y_sign == 0) or
               ((abs(self.prev_y_sign-y_sign)) > 1)):
                self.zero_ticker.mul = 0.0
                self.zero_ticker.reset()
                self.zero_ticker.frequency = main_freq
                self.zero_ticker.mul.linear_ramp_to_value(0.05, 0.7)
                self.zero_ticker.mul.linear_ramp_to_value(0.1, 0.0)
                self.zero_ticker.frequency.linear_ramp_to_value(0.07, main_freq**semitone)
        self.prev_y_sign = y_sign
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
