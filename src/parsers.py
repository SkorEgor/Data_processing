import pandas as pd


def parser_all_data(string_list: list) -> pd.DataFrame:
    """Парсит частоты и гамма-значения из строк, пропуская заголовок."""
    frequency_list = []
    gamma_list = []
    skipping_first_line = True
    for line in string_list:
        if skipping_first_line:
            skipping_first_line = False
            continue
        if line[0] == "*":
            break
        row = line.split()
        frequency_list.append(float(row[1]))
        gamma_list.append(float(row[4]))
    return pd.DataFrame({'frequency': frequency_list, 'gamma': gamma_list})


def parser_result_data(string_list: list) -> pd.DataFrame:
    """
    Парсит данные результата в частоты, гамма и флаг источника.

    Returns
    -------
    pandas.DataFrame
        DataFrame с колонками 'frequency', 'gamma', 'src' или None, если данных нет.
    """
    data = []
    for line in string_list:
        if "\t" in line and not line.startswith(("FREQ", "*")):
            freq, gam, src = line.strip().split("\t")
            data.append((float(freq), float(gam), src.lower() == "true"))
    if not data:
        return None
    freq, gamma, src = zip(*data)
    return pd.DataFrame({'frequency': freq, 'gamma': gamma, 'src': src})
