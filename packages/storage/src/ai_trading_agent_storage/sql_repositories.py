from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Connection

from ai_trading_agent_storage.metadata import (
    broker_accounts,
    broker_cash_snapshots,
    broker_commission_snapshots,
    broker_execution_snapshots,
    broker_position_snapshots,
    broker_reconciliation_differences,
    broker_reconciliation_reports,
    broker_sync_runs,
    external_broker_activities,
)
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    migration_readiness_is_safe_to_write,
)
from ai_trading_agent_storage.repository_contracts import *

class StoragePersistenceBlockedError(RuntimeError):
    pass


def ensure_persistence_allowed(report: MigrationReadinessReport) -> None:
    if not migration_readiness_is_safe_to_write(report):
        raise StoragePersistenceBlockedError("Persistence is geblokkeerd totdat migratiestatus schrijven toestaat.")


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _tuple_or_none(value: Any) -> tuple[str, ...] | None:
    return tuple(value) if value is not None else None


class _Base:
    def __init__(self, connection: Connection, readiness_report: MigrationReadinessReport) -> None:
        self._connection = connection
        self._readiness_report = readiness_report

    def _insert(self, table: Any, values: dict[str, Any]) -> None:
        ensure_persistence_allowed(self._readiness_report)
        self._connection.execute(table.insert().values(**values))

class SqlAlchemyBrokerAccountRepository(_Base):
    def get_by_id(self, broker_account_id: str) -> StorageReadResult[BrokerAccountRecord]:
        row = self._connection.execute(select(broker_accounts).where(broker_accounts.c.broker_account_id == broker_account_id)).mappings().first()
        if row is None:
            return StorageReadResult(False,None,broker_accounts.name,"Brokeraccount niet gevonden.")
        return StorageReadResult(True,BrokerAccountRecord(**row),broker_accounts.name,"Brokeraccount gevonden.")
    def list_accounts(self) -> StorageListResult[BrokerAccountRecord]:
        rows = self._connection.execute(select(broker_accounts)).mappings().all()
        return StorageListResult(tuple(BrokerAccountRecord(**r) for r in rows),broker_accounts.name,"Brokeraccounts opgehaald.")
    def save_account(self, record: BrokerAccountRecord) -> StorageWriteResult:
        self._insert(broker_accounts, asdict(record))
        return StorageWriteResult(True, record.broker_account_id, broker_accounts.name, True, "Brokeraccount opgeslagen.")

class SqlAlchemyBrokerSyncRunRepository(_Base):
    def get_by_id(self, broker_sync_run_id:str)->StorageReadResult[BrokerSyncRunRecord]:
        row=self._connection.execute(select(broker_sync_runs).where(broker_sync_runs.c.broker_sync_run_id==broker_sync_run_id)).mappings().first()
        if row is None:return StorageReadResult(False,None,broker_sync_runs.name,"Synchronisatierun niet gevonden.")
        row=dict(row); row['planned_data_kinds_json']=_tuple_or_none(row.get('planned_data_kinds_json')); row['data_source_types_json']=_tuple_or_none(row.get('data_source_types_json'))
        return StorageReadResult(True,BrokerSyncRunRecord(**row),broker_sync_runs.name,"Synchronisatierun gevonden.")
    def list_for_account(self,broker_account_id:str)->StorageListResult[BrokerSyncRunRecord]:
        rows=self._connection.execute(select(broker_sync_runs).where(broker_sync_runs.c.broker_account_id==broker_account_id)).mappings().all(); out=[]
        for r in rows:
            d=dict(r); d['planned_data_kinds_json']=_tuple_or_none(d.get('planned_data_kinds_json')); d['data_source_types_json']=_tuple_or_none(d.get('data_source_types_json')); out.append(BrokerSyncRunRecord(**d))
        return StorageListResult(tuple(out),broker_sync_runs.name,"Synchronisatieruns opgehaald.")
    def save_sync_run(self,record:BrokerSyncRunRecord)->StorageWriteResult:
        values=asdict(record); values['planned_data_kinds_json']=list(record.planned_data_kinds_json) if record.planned_data_kinds_json is not None else None; values['data_source_types_json']=list(record.data_source_types_json) if record.data_source_types_json is not None else None
        self._insert(broker_sync_runs,values); return StorageWriteResult(True,record.broker_sync_run_id,broker_sync_runs.name,True,"Synchronisatierun opgeslagen.")

class SqlAlchemyBrokerSnapshotRepository(_Base):
    def _list(self,table:Any,col:str,val:str,ctor:Any)->StorageListResult[Any]:
        rows=self._connection.execute(select(table).where(getattr(table.c,col)==val)).mappings().all(); out=[]
        for r in rows:
            d=dict(r)
            for k in ('quantity','average_cost','market_value','cash_amount','price','commission_amount','realized_pnl'):
                if k in d: d[k]=_to_decimal(d[k])
            if 'source_reference_ids_json' in d: d['source_reference_ids_json']=_tuple_or_none(d['source_reference_ids_json'])
            out.append(ctor(**d))
        return StorageListResult(tuple(out),table.name,f"{table.name} opgehaald.")
    def list_position_snapshots(self,broker_sync_run_id:str): return self._list(broker_position_snapshots,'broker_sync_run_id',broker_sync_run_id,BrokerPositionSnapshotRecord)
    def list_cash_snapshots(self,broker_sync_run_id:str): return self._list(broker_cash_snapshots,'broker_sync_run_id',broker_sync_run_id,BrokerCashSnapshotRecord)
    def list_execution_snapshots(self,broker_sync_run_id:str): return self._list(broker_execution_snapshots,'broker_sync_run_id',broker_sync_run_id,BrokerExecutionSnapshotRecord)
    def list_commission_snapshots(self,broker_sync_run_id:str): return self._list(broker_commission_snapshots,'broker_sync_run_id',broker_sync_run_id,BrokerCommissionSnapshotRecord)
    def save_position_snapshot(self,record:BrokerPositionSnapshotRecord)->StorageWriteResult:
        v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; self._insert(broker_position_snapshots,v); return StorageWriteResult(True,record.broker_position_snapshot_id,broker_position_snapshots.name,True,"Positiemomentopname opgeslagen.")
    def save_cash_snapshot(self,record:BrokerCashSnapshotRecord)->StorageWriteResult:
        v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; self._insert(broker_cash_snapshots,v); return StorageWriteResult(True,record.broker_cash_snapshot_id,broker_cash_snapshots.name,True,"Cashmomentopname opgeslagen.")
    def save_execution_snapshot(self,record:BrokerExecutionSnapshotRecord)->StorageWriteResult:
        v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; self._insert(broker_execution_snapshots,v); return StorageWriteResult(True,record.broker_execution_snapshot_id,broker_execution_snapshots.name,True,"Uitvoeringsmomentopname opgeslagen.")
    def save_commission_snapshot(self,record:BrokerCommissionSnapshotRecord)->StorageWriteResult:
        v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; self._insert(broker_commission_snapshots,v); return StorageWriteResult(True,record.broker_commission_snapshot_id,broker_commission_snapshots.name,True,"Commissiemomentopname opgeslagen.")

class SqlAlchemyBrokerReconciliationRepository(_Base):
    def get_report_by_id(self,broker_reconciliation_report_id:str):
        row=self._connection.execute(select(broker_reconciliation_reports).where(broker_reconciliation_reports.c.broker_reconciliation_report_id==broker_reconciliation_report_id)).mappings().first();
        return StorageReadResult(False,None,broker_reconciliation_reports.name,"Reconciliatierapport niet gevonden.") if row is None else StorageReadResult(True,BrokerReconciliationReportRecord(**dict(row)),broker_reconciliation_reports.name,"Reconciliatierapport gevonden.")
    def list_reports_for_sync_run(self,broker_sync_run_id:str):
        rows=self._connection.execute(select(broker_reconciliation_reports).where(broker_reconciliation_reports.c.broker_sync_run_id==broker_sync_run_id)).mappings().all(); return StorageListResult(tuple(BrokerReconciliationReportRecord(**dict(r)) for r in rows),broker_reconciliation_reports.name,"Reconciliatierapporten opgehaald.")
    def list_differences_for_report(self,broker_reconciliation_report_id:str):
        rows=self._connection.execute(select(broker_reconciliation_differences).where(broker_reconciliation_differences.c.broker_reconciliation_report_id==broker_reconciliation_report_id)).mappings().all(); out=[]
        for r in rows:
            d=dict(r); d['source_reference_ids_json']=_tuple_or_none(d.get('source_reference_ids_json')); d['audit_event_ids_json']=_tuple_or_none(d.get('audit_event_ids_json')); out.append(BrokerReconciliationDifferenceRecord(**d))
        return StorageListResult(tuple(out),broker_reconciliation_differences.name,"Reconciliatieverschillen opgehaald.")
    def save_report(self,record): self._insert(broker_reconciliation_reports,asdict(record)); return StorageWriteResult(True,record.broker_reconciliation_report_id,broker_reconciliation_reports.name,True,"Reconciliatierapport opgeslagen.")
    def save_difference(self,record): v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; v['audit_event_ids_json']=list(record.audit_event_ids_json) if record.audit_event_ids_json is not None else None; self._insert(broker_reconciliation_differences,v); return StorageWriteResult(True,record.broker_reconciliation_difference_id,broker_reconciliation_differences.name,True,"Reconciliatieverschil opgeslagen.")

class SqlAlchemyExternalBrokerActivityRepository(_Base):
    def get_by_id(self,external_broker_activity_id:str):
        row=self._connection.execute(select(external_broker_activities).where(external_broker_activities.c.external_broker_activity_id==external_broker_activity_id)).mappings().first()
        if row is None:return StorageReadResult(False,None,external_broker_activities.name,"Externe brokeractiviteit niet gevonden.")
        d=dict(row); d['source_reference_ids_json']=_tuple_or_none(d.get('source_reference_ids_json')); d['audit_event_ids_json']=_tuple_or_none(d.get('audit_event_ids_json')); return StorageReadResult(True,ExternalBrokerActivityRecord(**d),external_broker_activities.name,"Externe brokeractiviteit gevonden.")
    def list_for_account(self,broker_account_id:str):
        rows=self._connection.execute(select(external_broker_activities).where(external_broker_activities.c.broker_account_id==broker_account_id)).mappings().all(); out=[]
        for r in rows:
            d=dict(r); d['source_reference_ids_json']=_tuple_or_none(d.get('source_reference_ids_json')); d['audit_event_ids_json']=_tuple_or_none(d.get('audit_event_ids_json')); out.append(ExternalBrokerActivityRecord(**d))
        return StorageListResult(tuple(out),external_broker_activities.name,"Externe brokeractiviteiten opgehaald.")
    def save_external_activity(self,record): v=asdict(record); v['source_reference_ids_json']=list(record.source_reference_ids_json) if record.source_reference_ids_json is not None else None; v['audit_event_ids_json']=list(record.audit_event_ids_json) if record.audit_event_ids_json is not None else None; self._insert(external_broker_activities,v); return StorageWriteResult(True,record.external_broker_activity_id,external_broker_activities.name,True,"Externe brokeractiviteit opgeslagen.")

class SqlAlchemyBrokerStorageUnitOfWork:
    def __init__(self, connection: Connection, readiness_report: MigrationReadinessReport) -> None:
        self._connection=connection; self._readiness_report=readiness_report
        self.broker_accounts=SqlAlchemyBrokerAccountRepository(connection,readiness_report)
        self.broker_sync_runs=SqlAlchemyBrokerSyncRunRepository(connection,readiness_report)
        self.broker_snapshots=SqlAlchemyBrokerSnapshotRepository(connection,readiness_report)
        self.broker_reconciliation=SqlAlchemyBrokerReconciliationRepository(connection,readiness_report)
        self.external_broker_activities=SqlAlchemyExternalBrokerActivityRepository(connection,readiness_report)
    def health(self)->RepositoryHealthStatus:
        return RepositoryHealthStatus(True,self._readiness_report.database_connected,self._readiness_report.status.value=='migrations_current',not migration_readiness_is_safe_to_write(self._readiness_report),"Repository-status op basis van aangeleverde readiness.")
    def commit(self)->None: return None
    def rollback(self)->None: return None
