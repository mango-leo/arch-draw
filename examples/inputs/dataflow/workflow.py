from airflow.sdk import DAG
from airflow.providers.standard.operators.empty import EmptyOperator

with DAG(dag_id="orders_daily", schedule="@daily"):
    extract = EmptyOperator(task_id="extract")
    publish = EmptyOperator(task_id="publish")
    extract >> publish
