# Reset contract

Generated site state is disposable and must be recreated from content-addressed
manifests. Reset scripts may delete only a run-specific directory after resolving it
under the configured `artifacts/runs/<run_id>/web_state` root. The checked-in fixture
and source manifests are immutable inputs and must not be deleted by reset code.
