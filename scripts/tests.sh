SUPPORTED_VERSIONS=("3.8" "3.9" "3.10")
EXIT_CODES=()

for ver in "${SUPPORTED_VERSIONS[@]}"; do
  docker build -q --build-arg PYTHON_VERSION=$ver -t test_runtime_config_py . &&
    docker run --rm test_runtime_config_py
  EXIT_CODES+=($?)
  docker rmi -f test_runtime_config_py
done

printf "\n\n"

for code in "${EXIT_CODES[@]}"; do
  if [ "$code" -ne 0 ]; then
    echo "ON ONE OF THE VERSIONS OF PYTHON, THE TESTS DID NOT PASS!"
    exit 1
  fi
done

echo "ALL TESTS COMPLETED SUCCESSFULLY!"