/**
 * DisclaimerBanner — shown at the top of the chat.
 */
import './DisclaimerBanner.css';

function DisclaimerBanner({ tier, onDismiss }) {
  return (
    <div className={`disclaimer-banner disclaimer-banner--${tier || 'strong'}`}>
      <div className="disclaimer-banner__content">
        {tier === 'weak' ? (
          <>
            <i className='bx bx-user-circle disclaimer-banner__icon'></i>
            <p>
              <strong>Guest session — not saved.</strong>{' '}
              Sign in to keep your health history and get personalized answers.
            </p>
          </>
        ) : (
          <>
            <i className='bx bx-info-circle disclaimer-banner__icon'></i>
            <p>
              <strong>General health information only</strong> — not medical diagnoses or prescriptions.
              Always consult a healthcare professional for personal medical advice.
            </p>
          </>
        )}
      </div>
      <button className="disclaimer-banner__close" onClick={onDismiss} aria-label="Dismiss">
        <i className='bx bx-x'></i>
      </button>
    </div>
  );
}

export default DisclaimerBanner;
