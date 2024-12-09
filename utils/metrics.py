import sqlite3
import numpy as np
import scipy.stats
from collections import defaultdict

db = sqlite3.connect("amz_benchmark_data_20241105.sqlite")

query = """
SELECT AVG(t.value), engine_type.value, t.task, runs.workload
FROM runs, metrics AS t, tags AS engine_type, tags AS run_group
WHERE t.run_id = runs.id
AND engine_type.run_id = runs.id
AND run_group.run_id = runs.id
AND engine_type.name = 'engine-type'
AND run_group.name = 'run-group'
AND runs.distribution_version IN ('2.16.0', '8.15.0')
AND t.name = 'service_time'
AND t.sample_type = 'normal'
GROUP BY run_group.value, t.task
ORDER BY engine_type.value, t.task;
"""

data: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
    lambda: defaultdict(lambda: {"OS": list(), "ES": list()})
)

for service_time, engine_type, task, workload in db.execute(query).fetchall():
    data[workload][task][engine_type].append(service_time)


def norm_test(mean: float, std: float, samples: list[float]) -> float:
    norm = np.random.normal(mean, std, len(samples))
    return scipy.stats.ttest_ind(samples, norm).pvalue


def do_stats(engine, samples) -> tuple[float, float]:
    mean = np.mean(samples[engine])
    std = np.std(samples[engine])
    return (mean, std)

alpha=0.05
Z_alpha = scipy.stats.norm.ppf(alpha/2)

desired_power=0.9
Z_beta = scipy.stats.norm.ppf(desired_power)

print("workload,task,OS,OS stddev,OS normality,ES,ES stddev,ES normality,p,diff,log ratio,#OS samples,#ES samples,stat power,minimum sample size")
for workload, tasks in data.items():
    for task, engines in tasks.items():
        n_os = len(engines["OS"])
        n_es = len(engines["ES"])
        if n_os < 3 or n_es < 3:
            #print(
            #    f"Not enough samples for {workload} / {task}: {len(engines['OS'])} {len(engines['ES'])}"
            #)
            continue
        os_mean, os_std = do_stats("OS", engines)
        es_mean, es_std = do_stats("ES", engines)

        shap_os = scipy.stats.shapiro(engines["OS"])
        shap_es = scipy.stats.shapiro(engines["ES"])

        diff_p = scipy.stats.ttest_ind(engines["OS"], engines["ES"]).pvalue
        power_z = np.abs(os_mean - es_mean) / np.sqrt(os_std/n_os + es_std/n_es) + Z_alpha
        power = scipy.stats.norm.sf(-power_z)

        n = np.ceil(((os_std + es_std) * np.square(Z_beta - Z_alpha)) / np.square(os_mean - es_mean))
        print(
           f"{workload},{task},{os_mean},{os_std},{shap_os.pvalue},{es_mean},{es_std},{shap_es.pvalue},{diff_p},{np.abs(os_mean - es_mean)},{np.log2(es_mean/os_mean)},{n_os},{n_es},{power},{int(n)}"
        )
