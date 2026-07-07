from splunk_ao.resources.models import (
    LogRecordsBooleanFilter,
    LogRecordsDateFilter,
    LogRecordsIDFilter,
    LogRecordsNumberFilter,
    LogRecordsTextFilter,
)

FilterType = (
    LogRecordsBooleanFilter | LogRecordsDateFilter | LogRecordsIDFilter | LogRecordsNumberFilter | LogRecordsTextFilter
)
