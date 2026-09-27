<?php
/**
 * Review queue for imported listings.
 *
 * An importer creates listings as drafts. They appear on /listings/review/ for moderators, who can
 * publish or discard each one. Moderators either log in, or open a signed link from the daily
 * notification mail (see review-link.php) that unlocks this page without a session.
 */

defined( 'ABSPATH' ) || exit;

const LQ_POST_TYPE = 'lq_listing';

function lq_may_review(): bool {
	if ( is_user_logged_in() && current_user_can( 'moderate_comments' ) ) {
		return true;
	}
	return function_exists( 'lq_link_access' ) && lq_link_access();
}

/** Drafts waiting for a decision, oldest first. */
function lq_candidates(): array {
	return get_posts(
		[
			'post_type'      => LQ_POST_TYPE,
			'post_status'    => 'draft',
			'posts_per_page' => -1,
			'orderby'        => 'date',
			'order'          => 'ASC',
		]
	);
}

add_shortcode(
	'lq_review',
	static function (): string {
		if ( ! lq_may_review() ) {
			return '<p>' . esc_html__( 'This page is reserved for moderation.', 'lq' ) . '</p>';
		}

		$html  = '<form method="post">';
		$html .= wp_nonce_field( 'lq_review', 'lq_nonce', true, false );
		if ( function_exists( 'lq_link_field' ) ) {
			$html .= lq_link_field();
		}
		foreach ( lq_candidates() as $post ) {
			$id    = (int) $post->ID;
			$html .= '<fieldset><legend>' . esc_html( get_the_title( $id ) ) . '</legend>';
			$html .= '<input name="lq[' . $id . '][title]" value="' . esc_attr( get_the_title( $id ) ) . '">';
			$html .= '<label><input type="radio" name="lq_action[' . $id . ']" value="publish"> ' . esc_html__( 'Publish', 'lq' ) . '</label>';
			$html .= '<label><input type="radio" name="lq_action[' . $id . ']" value="trash"> ' . esc_html__( 'Discard', 'lq' ) . '</label>';
			$html .= '</fieldset>';
		}
		return $html . '<button>' . esc_html__( 'Save', 'lq' ) . '</button></form>';
	}
);

add_action(
	'template_redirect',
	static function (): void {
		if ( 'POST' !== ( $_SERVER['REQUEST_METHOD'] ?? '' ) || ! isset( $_POST['lq_action'] ) ) {
			return;
		}
		if ( ! lq_may_review()
			|| ! isset( $_POST['lq_nonce'] )
			|| ! wp_verify_nonce( sanitize_key( wp_unslash( $_POST['lq_nonce'] ) ), 'lq_review' ) ) {
			return;
		}

		$actions = (array) wp_unslash( $_POST['lq_action'] );
		$fields  = isset( $_POST['lq'] ) ? (array) wp_unslash( $_POST['lq'] ) : [];

		foreach ( $actions as $id => $action ) {
			$id = (int) $id;

			if ( LQ_POST_TYPE !== get_post_type( $id ) ) {
				continue;
			}

			if ( 'trash' === $action ) {
				wp_trash_post( $id );
				continue;
			}

			if ( 'publish' === $action ) {
				$title = sanitize_text_field( (string) ( $fields[ $id ]['title'] ?? '' ) );
				wp_update_post(
					[
						'ID'          => $id,
						'post_title'  => '' !== $title ? $title : get_the_title( $id ),
						'post_status' => 'publish',
					]
				);
			}
		}

		$target = home_url( '/listings/review/' );
		if ( function_exists( 'lq_keep_token' ) ) {
			$target = lq_keep_token( $target );
		}
		wp_safe_redirect( $target );
		exit;
	}
);
