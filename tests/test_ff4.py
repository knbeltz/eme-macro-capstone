import pandas as pd
import pytest

from eme_pipeline.ff4 import append_ff4, monthly_ff4


def test_monthly_sum_calendar_difference_and_missing_events():
    events = pd.DataFrame({'date': ['1999-12-15', '2000-01-05', '2000-01-20',
                                   '2000-03-01', '2000-03-02'],
                           'ff4_change_pp': [.1, .2, -.05, .3, float('nan')]})
    monthly = monthly_ff4(events)
    assert len(monthly) == 240
    assert monthly.iloc[0].us_ff4_monthly_change_pp == pytest.approx(.15)
    assert monthly.iloc[0].us_ff4_mom_change_pp == pytest.approx(.05)
    assert monthly.iloc[1].us_ff4_monthly_change_pp == 0
    assert monthly.iloc[1].us_ff4_mom_change_pp == pytest.approx(-.15)
    assert pd.isna(monthly.iloc[2].us_ff4_monthly_change_pp)
    assert pd.isna(monthly.iloc[3].us_ff4_mom_change_pp)
    frame = pd.DataFrame({'iso3': ['BRA', 'MEX'], 'date': ['2000-01'] * 2})
    result = append_ff4(frame, monthly)
    pd.testing.assert_frame_equal(result[frame.columns], frame)
    pd.testing.assert_frame_equal(append_ff4(result, monthly), result)
