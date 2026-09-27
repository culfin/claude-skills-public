<?php
/**
 * The signed link in the notification mail: opens the review page without logging in.
 *
 * The link does not create a session. It is bound to one moderator account, whose capability is
 * re-checked on every request, expires after 21 days, and only its hash is stored.
 */

defined( 'ABSPATH' ) || exit;

const LQ_LINK_OPTION = 'lq_review_tokens';
const LQ_LINK_PARAM  = 'lq_key';
const LQ_LINK_DAYS   = 21;

function lq_token_hash( string $token ): string {
	return hash( 'sha256', $token );
}

function lq_create_link_token( int $user_id ): string {
	$token  = bin2hex( random_bytes( 32 ) );
	$tokens = (array) get_option( LQ_LINK_OPTION, [] );

	$tokens[ lq_token_hash( $token ) ] = [
		'user'  => $user_id,
		'until' => time() + LQ_LINK_DAYS * DAY_IN_SECONDS,
	];
	update_option( LQ_LINK_OPTION, $tokens, false );

	return $token;
}

function lq_request_token(): string {
	$raw = $_POST[ LQ_LINK_PARAM ] ?? $_GET[ LQ_LINK_PARAM ] ?? '';
	$raw = is_string( $raw ) ? $raw : '';
	return preg_match( '/^[a-f0-9]{64}$/', $raw ) ? $raw : '';
}

function lq_link_access(): bool {
	static $cached = null;
	if ( null !== $cached ) {
		return $cached;
	}

	$token = lq_request_token();
	if ( '' === $token ) {
		return $cached = false;
	}

	$tokens = (array) get_option( LQ_LINK_OPTION, [] );
	foreach ( $tokens as $hash => $entry ) {
		if ( hash_equals( (string) $hash, lq_token_hash( $token ) ) && (int) ( $entry['until'] ?? 0 ) > time() ) {
			$user = get_user_by( 'id', (int) ( $entry['user'] ?? 0 ) );
			return $cached = ( $user && user_can( $user, 'moderate_comments' ) );
		}
	}
	return $cached = false;
}

function lq_link_field(): string {
	$token = lq_request_token();
	return '' === $token ? '' : '<input type="hidden" name="' . esc_attr( LQ_LINK_PARAM ) . '" value="' . esc_attr( $token ) . '">';
}

function lq_keep_token( string $url ): string {
	$token = lq_request_token();
	return '' === $token ? $url : add_query_arg( LQ_LINK_PARAM, $token, $url );
}

add_action(
	'wp_head',
	static function (): void {
		if ( lq_link_access() ) {
			echo '<meta name="robots" content="noindex"><meta name="referrer" content="no-referrer">';
		}
	}
);
