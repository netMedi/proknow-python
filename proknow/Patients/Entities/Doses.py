import os
import six
import time
import datetime

from .EntityItem import EntityItem
from ...Exceptions import InvalidPathError, TimeoutExceededError


class DoseItem(EntityItem):
    """

    This class represents a dose. It's instantiated by the :class:`proknow.Patients.EntitySummary`
    class as a complete representation of a dose entity.

    Attributes:
        id (str): The id of the entity (readonly).
        data (dict): The complete representation of the entity as returned from the API (readonly).

    """

    def __init__(self, patients, workspace_id, patient_id, entity):
        """Initializes the DoseItem class.

        Parameters:
            patients (proknow.Patients.Patients): The Patients instance that is instantiating the
                object.
            workspace_id (str): The id of the workspace to which the patient belongs.
            patient_id (str): The id of the patient to which the entity belongs.
            entity (dict): A dictionary of entity attributes.
        """
        super(DoseItem, self).__init__(patients, workspace_id, patient_id, entity)

    def _wait_analysis(self):
        start = datetime.datetime.now()
        DELAY = 0.2
        while (datetime.datetime.now() - start).total_seconds() < self._proknow.ENTITY_WAIT_TIMEOUT:
            analysis_status = self.data["data"]["analysis"]["status"]
            assert analysis_status != 'failed', "Dose analysis failed"
            assert analysis_status != 'pending', "Dose analysis not possible"
            if analysis_status == 'current':
                return
            else:
                time.sleep(DELAY)
                _, dose = self._requestor.get('/workspaces/' + self._workspace_id + '/doses/' + self._id)
                self._update(dose)
        raise TimeoutExceededError('Timeout exceeded while waiting for dose analysis to reach completed status') # pragma: no cover (should not occur in normal circumstances)

    def download(self, path):
        """Downloads the dose file.

        Parameters:
            path (str): A path to a directory or file to which the dose file should be streamed.

        Returns:
            str: The absolute path to the downloaded file.

        Raises:
            AssertionError: If the input parameters are invalid.
            :class:`proknow.Exceptions.HttpError`: If the HTTP request generated an error.
            :class:`proknow.Exceptions.InvalidPathError`: If the provided path is invalid.

        Example:
            This example shows how to download a dose file for a patient to the current directory::

                from proknow import ProKnow

                pk = ProKnow('https://example.proknow.com', credentials_file="./credentials.json")
                patients = pk.patients.lookup("Clinical", ["HNC-0522c0009"])
                patient = patients[0].get()
                entities = patient.find_entities(type="dose")
                dose = entities[0].get()
                dose.download("./")
        """
        assert isinstance(path, six.string_types), "`path` is required as a string."
        if os.path.isdir(path):
            resolved_path = os.path.join(os.path.abspath(path), "RD." + self._data["uid"] + ".dcm")
        else:
            absolute = os.path.abspath(path)
            directory = os.path.dirname(path)
            if os.path.isdir(directory):
                resolved_path = absolute
            else:
                raise InvalidPathError('`' + path + '` is invalid')

        self._requestor.stream('/workspaces/' + self._workspace_id + '/doses/' + self._id + '/dicom', resolved_path)
        return resolved_path

    def get_analysis(self):
        """Gets the analysis data for the dose.

        The analysis data consists primarily of DVH data.

        Note:
            For information on how interpret the dose analysis object, see :ref:`dose-analysis`.

        Returns:
            dict: The dose analysis data.

        Raises:
            AssertionError: If dose analysis cannot be computed because the dose is not associated
                with a structure set or if the dose analysis has failed.
            :class:`proknow.Exceptions.TimeoutExceededError`: If the timeout was exceeded while
                waiting for the analysis data to become available.
            :class:`proknow.Exceptions.HttpError`: If the HTTP request generated an error.

        Example:
            This example shows how to get the analysis data for a dose::

                from proknow import ProKnow

                pk = ProKnow('https://example.proknow.com', credentials_file="./credentials.json")
                patients = pk.patients.lookup("Clinical", ["HNC-0522c0009"])
                patient = patients[0].get()
                entities = patient.find_entities(type="dose")
                dose = entities[0].get()
                analysis = dose.get_analysis()
        """
        self._wait_analysis()
        headers = {
            'ProKnow-Key': self.data["key"]
        }
        _, content = self._requestor.get('/doses/' + self._id + '/analysis/' + self._data["data"]["analysis"]["tag"], headers=headers)
        return content

    def get_slice_data(self, index):
        """Gets the slice data for the dose at the given index.

        Parameters:
            index (int): The index of the slice for which to get the data.

        Returns:
            bytes: The slice data.

        Raises:
            AssertionError: If the input parameters are invalid.
            :class:`proknow.Exceptions.HttpError`: If the HTTP request generated an error.

        Example:
            This example shows how to get the slice data for each slice in a dose::

                from proknow import ProKnow

                pk = ProKnow('https://example.proknow.com', credentials_file="./credentials.json")
                patients = pk.patients.lookup("Clinical", ["HNC-0522c0009"])
                patient = patients[0].get()
                entities = patient.find_entities(type="dose")
                dose = entities[0].get()
                slice_count = len(dose.data["data"]["slices"])
                slice_data = [dose.get_slice_data(i) for i in range(slice_count)]
        """
        assert isinstance(index, int), "`index` is required as an integer."
        dose_slice = self.data["data"]["slices"][index]
        headers = {
            'ProKnow-Key': self.data["key"]
        }
        _, content = self._requestor.get_binary('/doses/' + self._id + '/slices/' + dose_slice["tag"], headers=headers)
        return content

    def refresh(self):
        """Refreshes the dose entity.

        Raises:
            :class:`proknow.Exceptions.HttpError`: If the HTTP request generated an error.

        Example:
            This example shows how to refresh a dose entity::

                from proknow import ProKnow

                pk = ProKnow('https://example.proknow.com', credentials_file="./credentials.json")
                patients = pk.patients.lookup("Clinical", ["HNC-0522c0009"])
                patient = patients[0].get()
                entities = patient.find_entities(type="dose")
                dose = entities[0].get()
                dose.refresh()
        """
        _, dose = self._requestor.get('/workspaces/' + self._workspace_id + '/doses/' + self._id)
        self._update(dose)
