# AUTOGENERATED! DO NOT EDIT! File to edit: pattern_finder.ipynb (unless otherwise specified).

__all__ = ['sankey_format', 'stringify_durations', 'interleave_strings', 'left_justify', 'overlay_strings', 'shorten',
           'shorten_interleaved', 'stringify_order', 'del_repeats', 'del_singles', 'stringify_time']

# Cell
from .utils import *

# Cell
from itertools import zip_longest

# Cell
def sankey_format(df, labels=None, normalize=False, dropna=False, threshold=0.01):
    """
    Format the dataframe so it is easy fo create a holoviews sankey figure

    labels=dict(bio_codes.values())
    import holoviews as hv
    hv.Sankey(t1).options(label_position='left')
    hv.extension('bokeh')
    t4=t1.copy()

    """
    a = df
    a = a.apply(lambda row: ' '.join(row))
    a = a.str.split(expand=True)

    a = a.replace(labels)
    for col in a.columns:
        a[col] = a[col] + ' (' + str(col + 1) + ')'


    if not dropna:
        a = a.fillna(f'No new')

    all_counts = {}
    for col in range(len(a.columns))[1:]:
        counts = a.groupby(a[col - 1])[col].value_counts(normalize=normalize)
        if normalize:
            counts = counts.mul(100).astype(int).fillna(0)

        counts.name = 'value'
        # counts = counts.rename(index=labels).reset_index()
        counts = counts.reset_index()
        counts.columns = ['source', 'target', 'value']

        all_counts[col] = counts
    t1 = pd.concat(all_counts, ignore_index=True)

    #if normalize:
    #    t1['value'] = t1['value'] / t1['value'].sum()

    t1 = t1[t1.source != 'No new']

    # a.groupby(1)[2].value_counts()
    return t1

# Cell
def stringify_durations(df,
                        codes=None,
                        cols=None,
                        pid='pid',
                        step=120,
                        sep=None,

                        event_start='in_date',
                        event_end=None,
                        event_duration='ddd',

                        first_date=None,
                        last_date=None,
                        censored_date=None,

                        ncodes=None,

                        no_event='-',
                        time_sep='|',

                        merge=True,
                        info=None,
                        report=False,
                        all_codes=None):
    """
    Creates a string for each individual describing the time duration selected code events (example: a-, ad, --, a)

    Args:
        df: dataframe
        codes: codes to be used to mark an event
        cols: columns with the event codes
        pid: column with the personal identification number
        event_start: column containing the date for the event
        sep: the separator used between events if a column has multiple events in a cell
        keep_repeats: identical events after each other are reduced to one (if true)
        only_unique: deletes all events that have occurred previously for the individual (if true)

    Returns:
        series with a string that describes the events for each individual
    Example:

    >>> codes={'i' : ['4AB02', 'L04AB02'], 'a': ['4AB04','L04AB04']}
    >>> events=sa.stringify_durations(df=mdf, codes=codes, cols='codes',
    event_start='date', first_date=None, sep=',', merge=True)

    >>> codes={'i' : ['4AB02', 'L04AB02'], 'a': ['4AB04','L04AB04']}
    >>> codes={'i' : ['L04*'], 'b': ['4AB04','L04AB04']}


    >>> codes = {'i':'L01BB02 L04AX03 L01BA01 L04AD01 L04AD02 L04AA06'.split(),
                 'b':'L04AB02 L04AB04 L04AB06 L04AA33 L04AC05 L04AA23'.split()}


    >>> events=sa.stringify_durations(df=mdf, codes=codes, cols='codes',
    event_start='date', first_date=None, sep=',', merge=False, step=100)

    >>> codes={'L04A*' : 'i', 'L04AB*' : 'a', 'H02*' : 'c'}
    >>> pr=pr.set_index('pid_index')
    >>> pr['first_date'] = pr.groupby('pid')['date'].min()
    >>> events=stringify_durations(df=df, codes=codes, col='ncmpalt', start='start_date', first_date='first', dataset_end_date="01-01-2018")


    background
        to identify treatment patters, first stringify each treatment,
        then aggregate the different treatments to one string
        each "cell" in the string (separated by sep) represent one time unit
        the time unit can be further aggregated to reduce the level of detail

    example output (one such row for each person)
        a---s, a---, ai-s, a---, ----

        Interpretation: A person with event a and s in first time perod, then a only in second,
        the a, i and s in the third, a only in fourth and no events in the last

    purpose
        examine typical treatment patterns and correlations
        use regex or other string operations on this to get statistcs
        (time on first line of treatment, number of switches, stops)

    """
    # drop rows with missing observations in required variable

    df = df.dropna(subset=[pid, event_start])

    if event_end:
        df = df.dropna(subset=[event_end])
    elif event_duration:
        df = df.dropna(subset=[event_duration])
        if df[event_duration].min() < 0:
            print('Error: The specified duration column contains negative values. They are dropped')
            df = df[df[event_duration] >= 0]
    else:
        print('Error: Either event_end or event_duration has to be specified.')

    # find default min and max dates
    # will be used as starting points for the string
    # if first_date and last_date are not specified
    min_date = df[event_start].min()
    max_date = df[event_start].max()

    # drop rows outside specified time period of interest
    if first_date:
        if first_date in df.columns:
            df = df[df[event_start] >= df[first_date]]
        elif isinstance(first_date, dict):
            pass
        else:
            # if first_date is not a column name, it is assumed to be a date
            try:
                min_date = pd.to_datetime(first_date)
                df = df[df[event_start] >= min_date]
            except:
                print('Error: The first_date argument has to be on of: None, a dict, a column name or a string that represents a date')

    if last_date:
        if last_date in df.columns:
            df = df[df[event_start] >= df[last_date]]
        elif isinstance(last_date, dict):
            pass
        else:
            try:
                max_date = pd.to_datetime(last_date)
                df = df[df[event_start] <= max_date]
            except:
                print('Error: The last_date argument has to be on of: None, a dict, a column name or a string the represents a date')

    # note an individual min date cannot be before overall specified min date
    # should raise error if user tries this
    # same with max: individual cannot be larger than overall

    max_length_days = (max_date - min_date).days
    max_length_steps = int(max_length_days / step)

    # # if codes are not specified, use the five most common codes
    # if not codes:
    #     cols = _expand_cols(_listify(cols))
    #     if not ncodes: ncodes = 4
    #     codes = count_codes(df=df, cols=cols, sep=sep).sort_values(ascending=False)[:ncodes]

    # fix formatting of input (make list out of a string input and so on)
    cols=expand_columns(cols, all_columns=list(df.columns))

    if not all_codes:
        all_codes = unique(df=df, cols=cols, sep=sep)
    codes = expand_code(codes, all_codes=all_codes, info=info)


    only_codes=[]
    for name, code in codes.items():
        only_codes.extend(code)
    print('only_codes', only_codes)

    # get the rows that contain the relevant codes
    rows = get_rows(df=df, codes=only_codes, cols=cols, sep=sep, fix=False)
    subset = df[rows].copy()  # maybe use .copy to avoid warnings? but takes time and memory
    subset = subset.set_index(pid, drop=False)
    subset.index.name = 'pid_index'
    subset = subset.sort_values([pid, event_start])

    if report:
        sub_obs = len(subset)
        sub_npid = subset[pid].nunique()

    # find start and end position of each event (number of steps from overall min_date)
    # to do: do not use those column names (may overwrite original names), use uuid names?
    subset['start_position'] = (subset[event_start] - min_date).dt.days.div(step).astype(int)

    if event_end:
        subset['end_position'] = (subset[event_end] - min_date).dt.days.div(step).astype(int)
    elif event_duration:
        subset['end_date'] = subset[event_start] + pd.to_timedelta(subset[event_duration].astype(int), unit='D')
        subset['end_position'] = (subset['end_date'] - min_date).dt.days.div(step).astype(int)

    # to do: may allow duration dict?
    # for instance: some drugs last 15 days, some drugs last 25 days . all specified in a dict

    # create series with only the relevant codes for each person and position
    code_series = extract_codes(df=subset.set_index([pid, 'start_position', 'end_position']),
                                codes=codes,
                                cols=cols,
                                sep=sep,
                                new_sep=',',
                                merge=False,
                                out='text',
                                all_codes=all_codes,
                                fix=False)

    unique_codes = list(code_series.columns)

    code_series = pd.melt(code_series.reset_index(),
                          id_vars=['pid', 'start_position', 'end_position'],
                          value_vars=unique_codes)

    # drop duplicates (same type of even in same period for same individual)
    code_series = code_series.drop_duplicates().set_index(pid, drop=False)
    code_series.index.name = 'pid_index'
    ## make dict with string start and end positions for each individual
    # explanation:
    # the string is first made marking events in positions using calendar time
    # but often we want the end result to be strings that start at specified
    # individual dates, and not the same calendar date for all
    # for instance it is often useful to start the string at the date the
    # person receives a diagnosis
    # same with end of string: strings may end when a patient dies
    # user can specify start and end dates by pointing to columns with dates
    # or they may specify an overall start and end date
    # if individual dates are specified, the long string based on calendar
    # time is sliced to include only the relevant events

    if first_date:
        # if a column is specified
        if first_date in subset.columns:
            start_date = subset.groupby(pid)[first_date].first().dropna().to_dict()
        # do nothing if a dict mapping pids to last_dates is already specified
        elif isinstance(first_date, dict):
            pass
        # if a single overall date is specified
        else:
            date = pd.to_datetime(first_date)
            start_date = {pid: date for pid in subset[pid].unique()}
        # convert start date to start position in string
        string_start_position = {pid: int((date - min_date).days / step)
                                 for pid, date in start_date.items()}

    if last_date:
        if last_date in subset:
            end_date = subset.groupby(pid)[last_date].first().dropna().to_dict()
        # do nothing if a dict mapping pids to last_dates is already specified
        elif isinstance(last_date, dict):
            pass
        else:
            date = pd.to_datetime(last_date)
            end_date = {pid: date for pid in subset[pid].unique()}
        # convert date to position in string
        string_end_position = {pid: int(((date - min_date).days)/step)
                               for pid, date in end_date.items()}

        # takes dataframe for an individual and makes a string with the events

    def make_string(events, code):
        # get pid of individual (required to find correct start and end point)
        person = events.index[0]

        # make a list of maximal length with no events
        event_list = [no_event] * (max_length_steps + 1)

        from_to_positions = tuple(zip(events['start_position'].tolist(), events['end_position'].tolist()))

        # loop over all events the individual has and put code in correct pos.
        for pos in from_to_positions:
            length=pos[1]-pos[0]
            event_list[pos[0]:pos[1]] = [code]*length
        event_string = "".join(event_list)

        # slice to correct start and end of string (if specified)
        # if first_date:
        #     event_string = event_string[string_start_position[person]:]
        # if last_date:
        #     max_position = int((max_date - min_date).days / step)
        event_string = event_string[string_start_position[person] : string_end_position[person]+1]
        return event_string

    # new dataframe to store each string for each individual for each code
    string_df = pd.DataFrame(index=code_series[pid].unique())
    string_df.index.name = 'pid_index'

    # loop over each code, aggregate strong for each individual, store in df
    for code in unique_codes:
        code_df = code_series[code_series['value'].isin([code])] # maybe == is better (safer bco compounds + faster?)
        stringified = code_df.groupby(pid, sort=False).apply(make_string, code)
        string_df[code] = stringified

    if merge:
        string_df = interleave_strings(string_df, no_event=no_event, time_sep=time_sep)

    if report:
        final_obs = len(subset)
        final_npid = len(string_df)
        print(f"""
                                     events,  unique ids
              Original dataframe     {obs}, {npid}
              Filter codes           {code_obs}, {code_npid}
              Filter missing         {sub_obs}, {sub_npid}
              Final result:          {final_obs}, {final_npid}""")
    return string_df

# Cell
def _make_binary(df, cols=None, no_event=' ', time_sep='|', pad=False):
    if isinstance(df, pd.Series):
        name = df[col].name
        df=df.str.replace(no_event, '0')
        df=df.str.replace(name, '1')
    else:
        # if no cols are selected, use all cols
        if not cols:
            cols = list(df.columns)
        # replace event chars with 1 and no events with 0
        for col in cols:
            name = df[col].name
            df[col]=df[col].str.replace(no_event, '0')
            df[col]=df[col].str.replace(name, '1')
    return df

# Cell
def interleave_strings(df, cols=None, time_sep="|", no_event=' ', agg=False):
    """
    Interleaves strings in two or more columns

    parameters
        cols : list of columns with strings to be interleaved
        nan : value to be used in place of missing values
        sep : seperator to be used between time periods
        agg : numeric, used to indicate aggregation of time scale
                default is 1

    background
        to identify treatment patters, first stringify each treatment,
        then aggregate the different treatments to one string
        each "cell" in the string (separated by sep) represent one time unit
        the time unit can be further aggregated to reduce the level of detail

    example output (one such row for each person)
        a---s, a---, ai-s, a---, ----

        Interpretation: A person with event a and s in first time perod, then a only in second,
        the a, i and s in the third, a only in fourth and no events in the last

    purpose
        examine typical treatment patterns and correlations
        use regex or other string operations on this to get statistcs
        (time on first line of treatment, number of switches, stops)

    """
    # if cols is not specified, use all columns in dataframe
    if not cols:
        cols = list(df.columns)

    if agg:
        for col in cols:
            df[col] = df[col].fillna(no_event)
            # find event symbol, imply check if all are missing, no events
            try:
                char = df[col].str.cat().strip().str.strip('-')[0]  # improvable?
            except:
                df[col] = (col.str.len() / agg) * no_event

            def aggregator(text, agg):
                missing = no_event * agg
                units = (text[i:i + agg] for i in range(0, len(text), agg))
                new_aggregated = (no_event if unit == missing else char for unit in units)
                new_str = "".join(new_aggregated)
                return new_str
        df[col] = df[col].apply(aggregator, agg=agg)

    if time_sep:
        interleaved = df[cols].fillna(no_event).apply(
            (lambda x: time_sep.join(
                "".join(i)
                for i in zip_longest(*x, fillvalue=no_event))),
            axis=1)
    else:
        interleaved = df[cols].fillna('-').apply(
            (lambda x: "".join(chain(*zip_longest(*x, fillvalue=no_event)))),
            axis=1)

    return interleaved

# Cell
def left_justify(s, fill=' '):
    """
    after stringify, to make events at same time be in same position
    and no, not as crucial as left-pad!
    """
    nmax = s.apply(len).max()
    s = s.str.pad(width=nmax, side='right', fillchar=fill)
    return s

# Cell
def overlay_strings(df, cols=None, sep=",", nan='-', collisions='x', interleaved=False):
    """
    overlays strings from two or more columns

    note
        most useful when aggregating a string for events that usually do not happen in the same time frame

    parameters
        cols : list of columns with strings to be interleaved
        nan : value to be used in place of missing values
        collisions: value to be used if there is a collision between events in a position


    background
        to identify treatment patters, first stringify each treatment,
        then aggregate the different treatments to one string
        each "cell" in the string (separated by sep) represent one time unit
        the time unit can be further aggregated to reduce the level of detail

    example output (one such row for each person)
        asaaa--s--aa-s-a

        Interpretation: A person with event a and s in first time perod, then a only in second,
        the a, i and s in the third, a only in fourth and no events in the last

    purpose
        examine typical treatment patterns and correlations
        use regex or other string operations on this to get statistcs
        (time on first line of treatment, number of switches, stops)

    todo
        more advanced handling of collisions
            - special symbols for different types of collisions
            - warnings (and keep/give info on amount and type of collisions)

    """
    # if cols is not specified, use all columns in dataframe
    if not cols:
        cols = list(df.columns)

    interleaved = df[cols].fillna('-').apply(
        (lambda x: "".join(chain(*zip_longest(*x, fillvalue='-')))),
        axis=1)
    step_length = len(cols)

    def event_or_collision(events):
        try:
            char = events.strip('-')[0]
        except:
            char = '-'
        n = len(set(events).remove('-'))
        if n > 1:
            char = 'x'
        return char

    def overlay_individuals(events):

        units = (events[i:i + step_length] for i in range(0, len(events), step_length))

        new_aggregated = (event_or_collision(unit) for unit in units)
        new_str = "".join(new_aggregated)
        return new_str

    interleaved.apply(overlay_individuals)

    return interleaved

# Cell
def shorten(events, agg=3, no_event=' '):
    """
    create a new and shorter string with a longer time step

    parameters
        events: (str) string of events that will be aggregated
        agg: (int) the level of aggregation (2=double the step_length, 3=triple)
    """
    try:
        char = events.strip(no_event)[0]
    except:
        char = no_event
    units = (events[i:i + agg] for i in range(0, len(events), agg))
    new_aggregated = (no_event if unit == no_event else char for unit in units)
    new_str = "".join(new_aggregated)
    return new_str

# Cell
def shorten_interleaved(text, agg=3, time_sep=',', no_event=' '):
    """
    text="a-si,a--i,a-s-,--si,---i,--s-"

    shorten_interleaved(c, agg=2)

    the original string must have a distinction between time_sep and no_event_sep
    (if not, could try to infer)
    """
    units = text.split(time_sep)
    ncodes = len(units[0])
    nunits = len(units)

    unitlist = [units[i:i + agg] for i in range(0, nunits, agg)]
    charlist = ["".join(aggunit) for aggunit in unitlist]
    unique_char = ["".join(set(chain(chars))) for chars in charlist]
    new_str = time_sep.join(unique_char)
    # ordered or sorted?
    # delete last if it is not full ie. not as many timee units in it as the others?
    # shortcut for all
    return new_str

# Cell
def stringify_order(df, codes=None, cols=None, pid='pid', event_start='date',
                    sep=None, time_sep='', first_date=None, last_date=None, period=None, keep_repeats=True,
                    only_unique=False, fix=True):
    """
    Creates a string for each individual describing selected code events in the order they occurred

    Args:
        df: dataframe
        codes: codes to be used to mark an event
        cols: columns with the event codes
        pid: column with the personal identification number
        event_start: column containing the date for the event
        sep: the separator used between events if a column has multiple events in a cell
        keep_repeats: identical events after each other are reduced to one (if true)
        only_unique: deletes all events that have occurred previously for the individual (if true)

    Returns:
        series with a string that describes the events for each individual



    Examples:

    >>> bio_codes= {'L04AA23': 'n', 'L04AA33': 'v', 'L04AB02': 'i', 'L04AB04': 'a','L04AB06': 'g', 'L04AC05': 'u'}

    >>> bio_codes={'e' : '4AB01', 'i' : '4AB02', 'a' : '4AB04'}

    >>> bio_codes={'i' : '4AB02', 'a' : '4AB04'}

    >>> bio_codes= {'n': ['L04AA23', '4AA23'],
                    'v': ['L04AA33', '4AA33'],
                    'i': ['L04AB02', '4AB02'],
                    'a': ['L04AB04', '4AB04'],
                    'g': ['L04AB06', '4AB06'],
                    'u': ['L04AC05', '4AC05']}


    >>> a=stringify_order(df=df, codes=bio_codes, cols='ncmpalt', pid='pid', event_start='start_date', sep=',', keep_repeats=True, only_unique=False)

    >>> a=sa.stringify_order(df=mdf, codes=bio_codes, cols='codes', pid='pid', first_date='first_ibd',
    event_start='date', sep=',', keep_repeats=False, only_unique=False, time_sep='', period=700)


    >>> bio_rows=get_rows(df=pr, codes=list(codes.keys()), cols='atc')
    >>> pr['first_bio']=pr[bio_rows].groupby('pid')['date'].min()

    >>> stringify_order(df=pr, codes=codes, cols='atc', pid='pid', event_date='date', sep=',')

    >>> stringify_order(df=pr, codes=bio_codes, cols='codes', pid='pid', event_date='date', sep=',')


    background
        to identify treatment patters, first stringify each treatment,
        then aggregate the different treatments to one string
        each "cell" in the string (separated by sep) represent one time unit
        the time unit can be further aggregated to reduce the level of detail

    example output (one such row for each person)
        a---s, a---, ai-s, a---, ----

        Interpretation: A person with event a and s in first time perod, then a only in second,
        the a, i and s in the third, a only in fourth and no events in the last

    purpose
        examine typical treatment patterns and correlations
        use regex or other string operations on this to get statistcs
        (time on first line of treatment, number of switches, stops)
    """
    print('no3')
    df.index.name = 'pid_index'  # avoid errors, and yes, require pid to be in index (?)

    df = df.dropna(subset=[pid, event_start])

    # example only include events after first diagnosis
    if first_date:
        df = df.dropna(subset=[first_date])

        # if a column is specified
        if first_date in df.columns:
            include = (df[event_start] >= df[first_date])
            # if a single overall date is specified
        else:
            date = pd.to_datetime(first_date)
            include = (df[event_start] >= date)
        df = df[include]

    # exclude events after ...
    if last_date:
        df = df.dropna(subset=[last_date])

        if last_date in df.columns:
            include = (df[event_start] <= df[last_date])
        else:
            date = pd.to_datetime(last_date)
            include = (df[event_start] <= df[last_date])
        df = df[include]

    # period represents the days from the first_date to be included
    # cannot specify both period and last_date(?)
    if period:
        if first_date:
            end_date = df[first_date] + pd.to_timedelta(period, unit='D')
            include = (df[event_start] <= end_date)
        else:
            time_after = (df[event_start] - df.groupby(pid)[event_start].min()) / np.timedelta64(1, 'D')
            include = (time_after <= period).values  # strange need this, tries to reindex if not
        df = df[include]

    if isinstance(df, pd.Series):
        df=df.to_frame()
        cols = list(df.columns)

    # fix formatting of input
    if fix:
        all_codes = unique(df=df, cols=cols, sep=sep, all_str=True)
        codes = expand_code(codes, all_codes=all_codes)
        cols = expand_columns(cols, df=df)
        print('after stringified fix', codes)

    only_codes=[]
    for name, code in codes.items():
        only_codes.extend(code)

    # get the rows with the relevant columns
    rows = get_rows(df=df, codes=only_codes, all_codes=all_codes, cols=cols, sep=sep)
    subset = df[rows]  #  copy?
    subset.index.name = 'pid_index'
    subset = subset.sort_values(by=[pid, event_start]).set_index('pid')

    # extract relevant codes and aggregate for each person
    code_series = extract_codes(df=subset, codes=codes, cols=cols, sep=sep,
                                new_sep='', merge=True, out='text')

    #    if isinstance(code_series, pd.DataFrame):
    #        code_series = pd.Series(code_series)
    string_df = code_series.groupby(level=0).apply(lambda codes: codes.str.cat(sep=time_sep))

    # eliminate repeats in string
    if not keep_repeats:
        string_df = string_df.str.replace(r'([a-z])\1+', r'\1')

    if only_unique:
        def uniqify(text):
            while re.search(r'([a-z])(.*)\1', text):
                text = re.sub(r'([a-z])(.*)\1', r'\1\2', text)
            return text

        string_df = string_df.apply(uniqify)
    return string_df

# Cell
def del_repeats(str_series):
    """
    deletes consecutively repeated characters from the strings in a series

    """
    no_repeats = str_series.str.replace(r'([a-z])\1+', r'\1')
    return no_repeats

# Cell
def del_singles(text):
    """
    Deletes single characters from string
    todo: how to deal with first and last position ... delete it too?

    """
    # text with only one character are by definition singles
    if len(text) < 2:
        no_singles = ''
    else:
        no_singles = "".join([letter for n, letter in enumerate(text[1:-1], start=1) if
                              ((text[n - 1] == letter) or (text[n + 1] == letter))])
        # long textx may not have any singles, so check before continue
        if len(no_singles) < 1:
            no_singles = ''
        else:
            if text[0] == no_singles[0]:
                no_singles = text[0] + no_singles
            if text[-1] == no_singles[-1]:
                no_singles = no_singles + text[-1]

    return no_singles

# Cell
def stringify_time(df,
                   codes=None,
                   cols=None,
                   pid='pid',
                   sep=None,
                   step=90,

                   event_start='date',  # use start end
                   nfirst=None,  # ncodes

                   all_codes=None,
                   first_date=None,
                   # use just first, last, censored. Accept integers to indicate period/days relative to the start date
                   last_date=None,
                   censored_date=None,

                   time_sep='|',
                   no_event=' ',
                   collision='*',

                   merge=True,
                   info=None):
    """
    Creates a string for each individual describing events at position in time

    Args:
        df: dataframe
        codes: codes to be used to mark an event
        cols: columns with the event codes
        pid: column with the personal identification number
        event_start: column containing the date for the event
        sep: the seperator used between events if a column has multiple events in a cell
        keep_repeats: identical events after each other are reduced to one (if true)
        only_unique: deletes all events that have occurred previously for the individual (if true)

    Returns:
        series with a string that describes the events for each individual

    Example:
        codes={'i': '4AB02', 'a':'4AB04'}
        codes={'i': ['4AB02','L04AB02'], 'a': ['4AB04', 'L04AB04'], 'e':['4AB01']}


        df['diagnosis_date']=df[df.icdmain.fillna('').str.contains('K50|K51')].groupby('pid')['start_date'].min()

    a=stringify_time(df=mdf,  codes=codes, cols='codes', pid='pid', event_start='date',
    first_date='first_ibd', step=90, sep=',', no_event=' ', time_sep=' ')


    background
        to identify treatment patters, first stringify each treatment,
        then aggregate the different treatments to one string
        each "cell" in the string (separated by sep) represent one time unit
        the time unit can be further aggregated to reduce the level of detail

    example output (one such row for each person)
        a---s, a---, ai-s, a---, ----

        Interpretation: A person with event a and s in first time perod, then a only in second,
        the a, i and s in the third, a only in fourth and no events in the last

    purpose
        examine typical treatment patterns and correlations
        use regex or other string operations on this to get statistcs
        (time on first line of treatment, number of switches, stops)
    """

    # drop rows with missing observations in required variables
    df = df.dropna(subset=[pid, event_start])

    # find default min and max dates to be used if not user specified
    min_date = df[event_start].min()
    max_date = df[event_start].max()

    # drop rows outside time period of interest
    if first_date:
        if first_date in df.columns:
            df = df[df[event_start] >= df[first_date]]
        else:
            min_date = pd.to_datetime(first_date)
            df = df[df[event_start] >= min_date]

    if last_date:
        if last_date in df.columns:
            df = df[df[event_start] >= df[last_date]]
        else:
            max_date = pd.to_datetime(last_date)
            df = df[df[event_start] <= max_date]

    # note an individual min date cannot be before overall specified min date
    # should raise error if user tries this
    # same with max: individual cannot be larger than overall

    max_length_days = (max_date - min_date).days
    max_length_steps = int(max_length_days / step)

    # # if codes or nfirst are not specified, use the five most common codes
    # if not codes:
    #     cols = expand_columns(_listify(cols))
    #     if not nfirst: nfirst = 5
    #     codes = count_codes(df=df, cols=cols, sep=sep).sort_values(ascending=False)[:nfirst]

    # fix formatting of input (make list out of a string input and so on)

    cols=expand_columns(cols, all_columns=list(df.columns))
    if not all_codes:
        all_codes = unique(df=df, cols=cols, sep=sep)
    codes = expand_code(codes, all_codes=all_codes, info=info)

    only_codes = []
    print('after stringified fix', codes)

    only_codes=[]
    for name, code in codes.items():
        only_codes.extend(code)

    # get the rows that contain the relevant codes
    rows = get_rows(df=df, codes=only_codes, cols=cols, sep=sep, all_codes=all_codes, fix=False)
    subset = df[rows].copy()  # maybe use .copy to avoid warnings?
    subset.index.name = 'pid_index'

    # find position of each event (number of steps from overall min_date)
    subset['position'] = (subset[event_start] - min_date).dt.days.div(step).astype(int)

    subset = subset.sort_values(by=[pid, 'position']).set_index([pid, 'position'])

    # create series with only the relevant codes for each person and position
    code_series = extract_codes(df=subset,
                                codes=codes,
                                cols=cols,
                                sep=sep,
                                new_sep=',',
                                merge=True,
                                out='text',
                                fix=False)

    # base further aggregation on the new extracted series with its col and codes
    col = code_series.name
    codes = code_series.name.split(', ')

    # drop duplicates (same type of even in same period for same individual)
    code_series = code_series.reset_index().drop_duplicates().set_index(pid, drop=False)
    code_series.index.name = 'pid_index'

    ## make dict with string start end end positions for each individual
    # explanation:
    # the string is first made marking events in positions using calendar time
    # but often we want the end result to be strings that start at specified
    # individual dates, and not the same calendar date for all
    # for instance it is often useful to start the string at the date the
    # person receives a diagnosis
    # same with end of string: strings may end when a patient dies
    # user can specify start and end dates by pointing to columns with dates
    # or they may specify an overall start and end date
    # if individual dates are specified, the long string based on calendar
    # time is sliced to include only the relevant events

    if first_date:
        # if a column is specified
        if first_date in subset.columns:
            start_date = subset.groupby(pid)[first_date].first().dropna().to_dict()
        # if a single overall date is specified
        else:
            date = pd.to_datetime(first_date)
            start_date = {pid: date for pid in subset[pid].unique()}
        # convert start date to start position in string
        start_position = {pid: int((date - min_date).days / step)
                          for pid, date in start_date.items()}

    if last_date:
        if last_date in subset:
            end_date = subset.groupby(pid)[last_date].first().dropna().to_dict()
        else:
            date = pd.to_datetime(last_date)
            end_date = {pid: date for pid in subset[pid].unique()}
        # convert date to position in string
        end_position = {pid: (date - min_date).dt.days.div(step).astype(int)
                        for pid, date in end_date.items()}

    # takes dataframe for an individual and makes a string with the events
    def make_string(events):
        # get pid of individual (required to find correct start and end point)
        person = events[pid].iloc[0]

        # make a list of maximal length with no events
        event_list = [no_event] * (max_length_steps + 1)

        # loop over all events the individual has and put code in correct pos.
        for pos in events['position'].values:
            event_list[pos] = code

        event_string = "".join(event_list)

        # slice to correct start and end of string (if specified)
        if first_date:
            event_string = event_string[start_position[person]:]
        if last_date:
            event_string = event_string[:-(max_length_steps - end_position[person])]
        return event_string

    # new dataframe to store each string for each individual for each code
    string_df = pd.DataFrame(index=code_series[pid].unique())

    # loop over each code, create aggregate string for each individual, store in df
    for code in codes:
        code_df = code_series[code_series[col].isin([code])]
        stringified = code_df.groupby(pid, sort=False).apply(make_string)
        string_df[code] = stringified

    if merge:
        string_df = interleave_strings(string_df, no_event=no_event, time_sep=time_sep)
    return string_df