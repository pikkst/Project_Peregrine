import json
from pathlib import Path

import cv2
import numpy as np
from cv_bridge import CvBridge


class SavepointDatabase:
    """Savepoint database loader and matcher for VPR."""

    def __init__(self, db_path, logger=None):
        self.db_path = Path(db_path)
        self.landmarks = []
        self.logger = logger
        self.feature_extractor = cv2.ORB_create(2000)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    def load_database(self):
        """Load savepoint database images and poses from disk."""
        if self.logger:
            self.logger.info(f'Loading savepoint database from {self.db_path}')

        self.landmarks.clear()

        if not self.db_path.exists():
            raise FileNotFoundError(f'Savepoint database path not found: {self.db_path}')

        if self.db_path.is_file() and self.db_path.suffix.lower() == '.json':
            self._load_from_json(self.db_path)
        elif self.db_path.is_dir():
            self._load_from_directory(self.db_path)
        else:
            raise ValueError(f'Unsupported savepoint database path: {self.db_path}')

        if self.logger:
            self.logger.info(f'Loaded {len(self.landmarks)} savepoint landmarks')

    def _load_from_json(self, json_path: Path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict):
            entries = data.get('landmarks', [])
        elif isinstance(data, list):
            entries = data
        else:
            raise ValueError('Savepoint database JSON must contain a list or dict with landmarks')

        for item in entries:
            image_path = Path(item.get('image_path', ''))
            if not image_path.is_absolute():
                image_path = json_path.parent / image_path
            pose = item.get('pose', [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
            self._add_landmark(image_path, pose)

    def _load_from_directory(self, folder_path: Path):
        image_paths = sorted(
            folder_path.glob('*.png')
        ) + sorted(
            folder_path.glob('*.jpg')
        ) + sorted(
            folder_path.glob('*.jpeg')
        )

        if not image_paths:
            raise ValueError(f'No image files found in savepoint database directory: {folder_path}')

        for image_path in image_paths:
            pose = self._load_pose_for_image(image_path)
            self._add_landmark(image_path, pose)

    def _load_pose_for_image(self, image_path: Path):
        pose_file = image_path.with_suffix('.json')
        if pose_file.exists():
            with open(pose_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            pose = data.get('pose') if isinstance(data, dict) else None
            if isinstance(pose, list) and len(pose) == 7:
                return pose
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

    def _add_landmark(self, image_path: Path, pose):
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            if self.logger:
                self.logger.warning(f'Unable to read savepoint image: {image_path}')
            return

        keypoints, descriptors = self.feature_extractor.detectAndCompute(image, None)
        if descriptors is None or len(keypoints) == 0:
            if self.logger:
                self.logger.warning(f'No features found for savepoint image: {image_path}')
            return

        self.landmarks.append({
            'name': image_path.stem,
            'path': str(image_path),
            'pose': pose,
            'keypoints': keypoints,
            'descriptors': descriptors,
        })

    def match_superglue(self, query_features, database_features=None):
        """Match query features against the loaded database landmarks."""
        query_keypoints, query_descriptors = query_features
        if query_descriptors is None or len(query_descriptors) == 0:
            return -1, 0.0

        best_index = -1
        best_score = 0.0

        for idx, landmark in enumerate(self.landmarks):
            db_descriptors = landmark['descriptors']
            if db_descriptors is None or len(db_descriptors) == 0:
                continue

            matches = self.matcher.knnMatch(query_descriptors, db_descriptors, k=2)
            good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]
            score = len(good_matches) / max(1, min(len(query_descriptors), len(db_descriptors)))

            if score > best_score:
                best_score = float(score)
                best_index = idx

        return best_index, best_score


class SuperPointExtractor:
    """ORB-based feature extractor used for VPR inference."""

    def __init__(self):
        self.extractor = cv2.ORB_create(2000)

    def extract_features(self, cv_image):
        if cv_image is None:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 32), dtype=np.uint8)

        if len(cv_image.shape) == 3:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_image

        keypoints, descriptors = self.extractor.detectAndCompute(gray, None)
        if descriptors is None or len(keypoints) == 0:
            return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 32), dtype=np.uint8)

        keypoints_array = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        return keypoints_array, descriptors


class VPRModel:
    def __init__(self, db_path, logger=None):
        self.db_path = db_path
        self.database = SavepointDatabase(db_path, logger=logger)
        self.superpoint = SuperPointExtractor()
        self.bridge = CvBridge()
        if logger:
            logger.info('VPR Model initialized')

    def load_database(self):
        self.database.load_database()

    def infer(self, image_msg):
        cv_image = self.bridge.imgmsg_to_cv2(image_msg, desired_encoding='rgb8')
        keypoints, descriptors = self.superpoint.extract_features(cv_image)

        if descriptors is None or len(descriptors) == 0:
            raise RuntimeError('Unable to extract features from input image')

        best_match_idx, confidence = self.database.match_superglue((keypoints, descriptors))
        if best_match_idx < 0:
            raise RuntimeError('No savepoint match found')

        landmark_pose = self._get_landmark_pose(best_match_idx)
        covariance = self._compute_covariance(confidence)
        pose = np.array(landmark_pose, dtype=np.float64)
        return pose, covariance

    def _get_landmark_pose(self, landmark_idx):
        if 0 <= landmark_idx < len(self.database.landmarks):
            return self.database.landmarks[landmark_idx]['pose']
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

    def _compute_covariance(self, confidence):
        confidence = float(np.clip(confidence, 0.0, 1.0))
        uncertainty = max(0.01, 0.2 * (1.0 - confidence))
        covariance = np.eye(6, dtype=np.float64) * uncertainty
        return covariance
