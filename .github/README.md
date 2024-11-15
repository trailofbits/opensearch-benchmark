# How to modify jobs in CI

The `workload_params` argument can be used to overwrite the workload parameters
of a specific job. The user-specified parameters will overwrite all previously set parameter values for the workload

## Examples
### Overwrite parameters for all big5 workloads
```
{
    "big5": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for pmc on ES
```
{
    "pmc-es": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for pmc on ES but only on 8.15.0
```
{
    "pmc-es-8.15.0": {
        "new_arg": "value"
    }
}
```

### Overwrite parameters for big5 and pmc
```
{
    "pmc-es-8.15.0": {
        "new_arg": "value"
    },
    "big5": {
        "big5_param": "value2"
    }
}
```
