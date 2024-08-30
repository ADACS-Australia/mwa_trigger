ATCA_COLUMNS = [
    'atca_band_3mm',
    'atca_band_3mm_freq1',
    'atca_band_3mm_freq2',
    'atca_band_7mm',
    'atca_band_7mm_freq1',
    'atca_band_7mm_freq2',
    'atca_band_15mm',
    'atca_band_15mm_freq1',
    'atca_band_15mm_freq2',
    'atca_band_4cm',
    'atca_band_4cm_freq1',
    'atca_band_4cm_freq2',
    'atca_band_16cm',
    'atca_band_15mm_exptime',
    'atca_band_16cm_exptime',
    'atca_band_3mm_exptime',
    'atca_band_4cm_exptime',
    'atca_band_7mm_exptime',
    'atca_max_exptime',
    'atca_prioritise_source',
    'atca_min_exptime',
    'atca_dec_max_1',
    'atca_dec_max_2',
    'atca_dec_min_1',
    'atca_dec_min_2',
]

MWA_COLUMNS = [
    'start_observation_at_high_sensitivity',
    'mwa_freqspecs',
    'mwa_exptime',
    'mwa_calexptime',
    'mwa_freqres',
    'mwa_inttime',
    'mwa_horizon_limit',
    'mwa_sub_alt_NE',
    'mwa_sub_alt_NW',
    'mwa_sub_alt_SE',
    'mwa_sub_alt_SW',
    'mwa_sub_az_NE',
    'mwa_sub_az_NW',
    'mwa_sub_az_SE',
    'mwa_sub_az_SW',
]

GW_COLUMNS = [
    'minimum_neutron_star_probability',
    'maximum_neutron_star_probability',
    'early_observation_time_seconds',
    'minimum_binary_neutron_star_probability',
    'maximum_binary_neutron_star_probability',
    'minimum_neutron_star_black_hole_probability',
    'maximum_neutron_star_black_hole_probability',
    'minimum_binary_black_hole_probability',
    'maximum_binary_black_hole_probability',
    'minimum_terrestial_probability',
    'maximum_terrestial_probability',
    'maximum_false_alarm_rate',
    'observe_significant',
    'minimum_hess_significance',
    'maximum_hess_significance',
]

MAIN_COLUMNS = [
    'id',
    'telescope',
    'project_id',
    'proposal_id',
    'proposal_description',
    'maximum_observation_time_seconds',
    'priority',
    'event_telescope',
    'event_any_duration',
    'event_min_duration',
    'event_max_duration',
    'pending_min_duration_1',
    'pending_max_duration_1',
    'pending_min_duration_2',
    'pending_max_duration_2',
    'maximum_position_uncertainty',
    'fermi_prob',
    'swift_rate_signf',
    'antares_min_ranking',
    'repointing_limit',
    'testing',
    'source_type',
]

# abstarct class
DEFAULT_MAX_OBSERVATION_TIME_SECONDS = 0
DEFAULT_PRIORITY = 1
DEFAULT_EVENT_ANY_DURATION = False
DEFAULT_EVENT_MIN_DURATION = 0.256
DEFAULT_EVENT_MAX_DURATION = 1.024
DEFAULT_PENDING_MIN_DURATION_1 = 1.025
DEFAULT_PENDING_MAX_DURATION_1 = 2.056
DEFAULT_PENDING_MIN_DURATION_2 = 0.128
DEFAULT_PENDING_MAX_DURATION_2 = 0.255
DEFAULT_MAX_POSITION_UNCERTAINTY = 0.05
DEFAULT_FERMI_PROB = 50
DEFAULT_SWIFT_RATE_SIGNF = 0.0
DEFAULT_ANTARES_MIN_RANKING = 2
DEFAULT_REPOINTING_LIMIT = 10.0
DEFAULT_TESTING = "Option1"
DEFAULT_SOURCE_TYPE = "GW"  # Example, change as needed

# consts for GW settings
DEFAULT_MINIMUM_NEUTRON_STAR_PROBABILITY = 0.01
DEFAULT_MAXIMUM_NEUTRON_STAR_PROBABILITY = 1
DEFAULT_EARLY_OBSERVATION_TIME_SECONDS = 900
DEFAULT_MINIMUM_BINARY_NEUTRON_STAR_PROBABILITY = 0.01
DEFAULT_MAXIMUM_BINARY_NEUTRON_STAR_PROBABILITY = 1
DEFAULT_MINIMUM_NEUTRON_STAR_BLACK_HOLE_PROBABILITY = 0.01
DEFAULT_MAXIMUM_NEUTRON_STAR_BLACK_HOLE_PROBABILITY = 1
DEFAULT_MINIMUM_BINARY_BLACK_HOLE_PROBABILITY = 0.00
DEFAULT_MAXIMUM_BINARY_BLACK_HOLE_PROBABILITY = 1
DEFAULT_MINIMUM_TERRESTIAL_PROBABILITY = 0.00
DEFAULT_MAXIMUM_TERRESTIAL_PROBABILITY = 0.95
DEFAULT_MAXIMUM_FALSE_ALARM_RATE = "1.00e-8"
DEFAULT_OBSERVE_SIGNIFICANT = False
DEFAULT_MINIMUM_HESS_SIGNIFICANCE = 0.2
DEFAULT_MAXIMUM_HESS_SIGNIFICANCE = 1
DEFAULT_START_OBSERVATION_AT_HIGH_SENSITIVITY = False

# consts for MWA settings
DEFAULT_MWA_SUB_ALT_NE = 90.0
DEFAULT_MWA_SUB_AZ_NE = 0.0
DEFAULT_MWA_SUB_ALT_NW = 66.85
DEFAULT_MWA_SUB_AZ_NW = 270.0
DEFAULT_MWA_SUB_ALT_SW = 43.97
DEFAULT_MWA_SUB_AZ_SW = 270.0
DEFAULT_MWA_SUB_ALT_SE = 59.35
DEFAULT_MWA_SUB_AZ_SE = 219.88
DEFAULT_MWA_FREQSPECS = "144,24"
DEFAULT_MWA_EXPTIME = 896
DEFAULT_MWA_CALEXPTIME = 120.0
DEFAULT_MWA_FREQRES = 10.0
DEFAULT_MWA_INTTIME = 0.5
DEFAULT_MWA_HORIZON_LIMIT = 10.0

# consts for ATCA settings
DEFAULT_ATCA_BAND_3MM = False
DEFAULT_ATCA_BAND_3MM_EXPTIME = 60
DEFAULT_ATCA_BAND_3MM_FREQ1 = None
DEFAULT_ATCA_BAND_3MM_FREQ2 = None
DEFAULT_ATCA_BAND_7MM = False
DEFAULT_ATCA_BAND_7MM_EXPTIME = 60
DEFAULT_ATCA_BAND_7MM_FREQ1 = None
DEFAULT_ATCA_BAND_7MM_FREQ2 = None
DEFAULT_ATCA_BAND_15MM = False
DEFAULT_ATCA_BAND_15MM_EXPTIME = 60
DEFAULT_ATCA_BAND_15MM_FREQ1 = None
DEFAULT_ATCA_BAND_15MM_FREQ2 = None
DEFAULT_ATCA_BAND_4CM = False
DEFAULT_ATCA_BAND_4CM_EXPTIME = 60
DEFAULT_ATCA_BAND_4CM_FREQ1 = None
DEFAULT_ATCA_BAND_4CM_FREQ2 = None
DEFAULT_ATCA_BAND_16CM = False
DEFAULT_ATCA_BAND_16CM_EXPTIME = 60
DEFAULT_ATCA_MAX_EXPTIME = 720
DEFAULT_ATCA_MIN_EXPTIME = 30
DEFAULT_ATCA_PRIORITISE_SOURCE = False
DEFAULT_ATCA_DEC_MIN_1 = -90
DEFAULT_ATCA_DEC_MAX_1 = -5
DEFAULT_ATCA_DEC_MIN_2 = 5
DEFAULT_ATCA_DEC_MAX_2 = 20
