
sudo iptables -F
#avocado run performance_regression_test.py:PerformanceRegressionTest.test_foo --multiplex data_dir/jenkins_conf.yaml --filter-only /run/backends/aws/us_west_1 /run/databases/scylla --filter-out /run/backends/libvirt  --show-job-log
#avocado run performance_regression_test.py:PerformanceRegressionTest.test_simple_regression --multiplex data_dir/jenkins_conf.yaml --filter-only /run/backends/aws/us_west_1 /run/databases/scylla --filter-out /run/backends/libvirt  --show-job-log
avocado run performance_regression_test.py:PerformanceRegressionTest.test_simple_regression --multiplex data_dir/your_config.yaml --filter-only /run/backends/aws/us_west_1 /run/databases/scylla --filter-out /run/backends/libvirt  --show-job-log

