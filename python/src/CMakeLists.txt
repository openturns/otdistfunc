
install ( FILES core_dispatcher_launcher.py
                core_dispatcher.py
                DistributedPythonFunction.py
                distributed_wrapper.py
                host_dispatcher.py
                __init__.py
                remote_communicator.py
                wrapper_data.py
                wrapper_launcher.py
          DESTINATION ${OTDISTFUNC_PYTHON_MODULE_PATH}/${PACKAGE_NAME}
        )
